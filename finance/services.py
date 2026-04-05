import datetime
import math
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Asset, CashFlowSource, OneTimeEvent, Pension, PhysicalAsset, RealEstate
from core.models import UserProfile

class SimulationEngine:
    def __init__(self, user, simulation_params=None):
        self.user = user
        self.profile, created = UserProfile.objects.get_or_create(user=user)
        self.params = simulation_params or {}
        
        # Simulation Parameters from profile or override (with safe fallbacks for missing columns)
        def get_safe_decimal(params, field, profile_obj, default):
            try:
                # Try getting from simulation params first
                val = params.get(field)
                if val is None:
                    # Fallback to profile attribute
                    val = getattr(profile_obj, field, default)
                
                # FINAL safety: if it's still None (NULL in DB), use default
                if val is None:
                    val = default
                    
                return Decimal(str(val))
            except (AttributeError, TypeError, ValueError):
                return Decimal(str(default))

        self.inflation_rate = get_safe_decimal(self.params, 'inflation_rate', self.profile, 2.0) / 100
        self.salary_increase = get_safe_decimal(self.params, 'salary_increase', self.profile, 1.5) / 100
        self.pension_increase = get_safe_decimal(self.params, 'pension_increase', self.profile, 1.0) / 100
        self.investment_return_offset = get_safe_decimal(self.params, 'investment_return_offset', self.profile, 0.0) / 100

    def get_simulation_start_date(self):
        """
        Finds the earliest relevant date across all models for the user.
        Always returns at least the 1st of the current month.
        """
        today = datetime.date.today().replace(day=1)
        dates = [today]

        # Check Cash Flows
        cf_start = self.user.cash_flows.filter(start_date__isnull=False).order_by('start_date').first()
        if cf_start:
            dates.append(cf_start.start_date)

        # Check One Time Events
        event_start = self.user.events.order_by('date').first()
        if event_start:
            dates.append(event_start.date)
            
        # Check Pensions
        pension_start = self.user.pensions.filter(start_payout_date__isnull=False).order_by('start_payout_date').first()
        if pension_start:
            dates.append(pension_start.start_payout_date)
            
        # Check Assets
        asset_start = self.user.assets.filter(withdrawal_start_date__isnull=False).order_by('withdrawal_start_date').first()
        if asset_start:
            dates.append(asset_start.withdrawal_start_date)

        min_date = min(dates)
        # Normalize to the 1st of the month
        return min_date.replace(day=1)

    def get_forecast(self, months=None):
        start_date = self.get_simulation_start_date()
        
        # Reference Date (Stichtag) - Baseline for "Today/Current" metrics
        stichtag = self.params.get('stichtag')
        if isinstance(stichtag, str):
            try:
                stichtag = datetime.datetime.strptime(stichtag, '%Y-%m-%d').date().replace(day=1)
            except:
                stichtag = timezone.now().date().replace(day=1)
        if not stichtag:
            stichtag = timezone.now().date().replace(day=1)
        else:
            stichtag = stichtag.replace(day=1)

        if months is None:
            # Calculate total months from start_date until simulation_max_age
            if self.profile.birth_date:
                target_end = self.profile.birth_date + relativedelta(years=self.profile.simulation_max_age)
                # Fill up the last year to ensure yearly aggregations show full years
                end_date = datetime.date(target_end.year, 12, 31)
                diff = relativedelta(end_date, start_date)
                months = diff.years * 12 + diff.months + (1 if diff.days > 0 else 0)
                # Ensure we include at least one month
                months = max(1, months)
            else:
                months = 360 # Default 30 years
        
        months = max(1, min(months, 720)) 
        data = []
        
        # Initial State
        assets = list(self.user.assets.all())
        pensions = list(self.user.pensions.all())
        cash_flows = list(self.user.cash_flows.select_related('category').all())
        one_time_events = list(self.user.events.all())
        physical_assets = list(self.user.physical_assets.all())
        real_estates = list(self.user.real_estates.all())

        global_pa_growth = Decimal(str(self.params.get('physical_asset_growth_rate', 0.0)))
        global_re_growth = Decimal(str(self.params.get('real_estate_growth_rate', 0.0)))

        pensions_state = []
        for p in pensions:
            pensions_state.append({'pension': p, 'balance': p.current_value})
            
        assets_state = []
        for a in assets:
            assets_state.append({'asset': a, 'balance': a.value})
            
        physical_assets_state = []
        for pa in physical_assets:
            physical_assets_state.append({'asset': pa, 'balance': pa.value})
            
        real_estates_state = []
        for re in real_estates:
            real_estates_state.append({'asset': re, 'balance': re.property_value})
            
        accumulated_cash = Decimal('0.00')

        for i in range(months):
            current_date = start_date + relativedelta(months=i)
            # Inflation calculation relative to Simulation Start (today), not Stichtag
            today_normalized = datetime.date.today().replace(day=1)
            months_from_today = (current_date.year - today_normalized.year) * 12 + (current_date.month - today_normalized.month)
            year_passed_decimal = Decimal(str(max(0, months_from_today))) / 12
            # Inflation factor for real-value conversion is relative to Stichtag
            months_from_stichtag = (current_date.year - stichtag.year) * 12 + (current_date.month - stichtag.month)
            year_from_stichtag = Decimal(str(max(0, months_from_stichtag))) / 12

            # 1. Dynamic Pension Contributions and Payouts for this month
            current_monthly_pension_contribution = Decimal('0.00')
            current_monthly_pension_payout = Decimal('0.00')
            current_monthly_pension_payout_fixed = Decimal('0.00')
            current_monthly_pension_payout_capital = Decimal('0.00')
            
            for p_item in pensions_state:
                p = p_item['pension']
                # Contrib: only if before end date
                if not p.contribution_end_date or current_date < p.contribution_end_date.replace(day=1):
                    current_monthly_pension_contribution += p.monthly_contribution
                
                # Payout: only if after/at start payout date
                if p.start_payout_date and current_date >= p.start_payout_date.replace(day=1):
                    if p.expected_payout_at_retirement:
                        # Use the contract value but apply growth from start of payout until now
                        payout_val = Decimal(str(p.expected_payout_at_retirement))
                        
                        # Calculate full years since payout started for annual step-growth
                        years_since_start = (current_date.year - p.start_payout_date.year) * 12 + (current_date.month - p.start_payout_date.month)
                        full_years_since_start = Decimal(str(max(0, years_since_start) // 12))
                        
                        # Grow Nominal Payout by pension_increase rate annually (step function) if indexed
                        actual_increase = self.pension_increase if p.is_indexed else Decimal('0.00')
                        payout_val = payout_val * ((1 + actual_increase) ** full_years_since_start)
                        current_monthly_pension_payout += payout_val
                        
                        # Split by capital base
                        if p.current_value > 0:
                            current_monthly_pension_payout_capital += payout_val
                        else:
                            current_monthly_pension_payout_fixed += payout_val

            # 2. Process Cash Flows (Income/Expenses)
            monthly_income = current_monthly_pension_payout
            monthly_expenses = current_monthly_pension_contribution # Savings count as expense
            category_breakdown = {
                'Sparen': current_monthly_pension_contribution
            }
            income_category_breakdown = {}
            if current_monthly_pension_payout_fixed > 0:
                income_category_breakdown[str(_('Gesetzliche Rente'))] = current_monthly_pension_payout_fixed
            if current_monthly_pension_payout_capital > 0:
                income_category_breakdown[str(_('Private Kapital-Rente'))] = current_monthly_pension_payout_capital
            
            for cf in cash_flows:
                if cf.start_date and cf.start_date.replace(day=1) > current_date: continue
                if cf.end_date and cf.end_date.replace(day=1) < current_date: continue
                
                amount = cf.value
                if cf.is_inflation_adjusted:
                    rate = self.salary_increase if cf.is_income else self.inflation_rate
                    amount = amount * ((1 + rate) ** year_passed_decimal)

                val = amount if cf.frequency == 'monthly' else amount / 12

                if cf.is_income:
                    monthly_income += val
                    cat_name = cf.category.name if cf.category else "Uncategorized"
                    income_category_breakdown[cat_name] = income_category_breakdown.get(cat_name, Decimal('0')) + val
                else:
                    monthly_expenses += val
                    cat_name = cf.category.name if cf.category else "Uncategorized"
                    category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + val

            # Cash flows from PhysicalAssets and RealEstate
            for item in physical_assets_state:
                pa = item['asset']
                if pa.storage_costs_monthly:
                    val = pa.storage_costs_monthly
                    monthly_expenses += val
                    cat_name = str(_('Sachwerte (Kosten)'))
                    category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + val
                    
            for item in real_estates_state:
                re = item['asset']
                if re.rental_income_monthly:
                    val = re.rental_income_monthly
                    monthly_income += val
                    cat_name = str(_('Immobilien (Miete)'))
                    income_category_breakdown[cat_name] = income_category_breakdown.get(cat_name, Decimal('0')) + val
                
                costs = (re.maintenance_costs_monthly or Decimal('0'))
                if costs > 0:
                    monthly_expenses += costs
                    cat_name = str(_('Immobilien (Instandhaltung)'))
                    category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + costs

            # 3. One Time Events
            event_impact = Decimal('0.00')
            events_this_month = []
            for event in one_time_events:
                if event.date.year == current_date.year and event.date.month == current_date.month:
                    event_impact += event.value
                    events_this_month.append({
                        'name': event.name, 'description': event.description or '',
                        'date': event.date.isoformat(), 'value': float(round(event.value, 2)),
                    })

            # 4. Wealth Accumulation and Growth - Continuous Simulation
            # Apply Asset Growth & Withdrawals
            if i > 0: # Start growth from the second month
                for item in assets_state:
                    asset = item['asset']
                    rate = ((asset.growth_rate or Decimal('0.00')) / 100) + self.investment_return_offset
                    item['balance'] *= (1 + (rate / 12))
                    if asset.withdrawal_start_date and current_date >= asset.withdrawal_start_date.replace(day=1):
                        item['balance'] = max(Decimal('0'), item['balance'] - (asset.withdrawal_amount or Decimal('0.00')))
                
                # Apply Pension Growth & Contribution
                for item in pensions_state:
                    pension = item['pension']
                    # Growth applies to current balance
                    rate = (pension.growth_rate or Decimal('0.00')) / 100
                    item['balance'] *= (1 + (rate / 12))
                    # Contribution only if before end date
                    if not pension.contribution_end_date or current_date < pension.contribution_end_date.replace(day=1):
                        item['balance'] += (pension.monthly_contribution or Decimal('0.00'))

                # Apply Sachwerte Growth
                for item in physical_assets_state:
                    pa = item['asset']
                    # Sale Date Check
                    if pa.sale_date and current_date >= pa.sale_date:
                        item['balance'] = Decimal('0.00')
                        continue
                    if pa.is_sold and i == 0: # Already sold at simulation start
                        item['balance'] = Decimal('0.00')
                        continue
                        
                    rate = pa.appreciation_rate
                    if rate == 0 and global_pa_growth != 0:
                        rate = global_pa_growth
                        
                    item['balance'] *= (1 + (rate / 100 / 12))
                    
                # Apply Immobilien Growth
                for item in real_estates_state:
                    re = item['asset']
                    # Sale Date Check
                    if re.sale_date and current_date >= re.sale_date:
                        item['balance'] = Decimal('0.00')
                        continue
                    if re.is_sold and i == 0: # Already sold at simulation start
                        item['balance'] = Decimal('0.00')
                        continue

                    rate = re.appreciation_rate
                    if rate == 0 and global_re_growth != 0:
                        rate = global_re_growth

                    item['balance'] *= (1 + (rate / 100 / 12))

                # Monthly Savings: monthly_expenses already includes current_monthly_pension_contribution
                monthly_savings = monthly_income - monthly_expenses
                accumulated_cash += (monthly_savings + event_impact)
            
            # Totals
            asset_total = sum(item['balance'] for item in assets_state)
            pension_total = sum(item['balance'] for item in pensions_state)
            physical_asset_total = sum(item['balance'] for item in physical_assets_state)
            real_estate_total = sum(item['balance'] for item in real_estates_state)
            
            total_nominal = asset_total + pension_total + accumulated_cash
            
            # Inflation Factor for Real Value (Purchasing Power relative to Stichtag)
            inflation_factor = (1 + self.inflation_rate) ** year_from_stichtag
            total_real = total_nominal / inflation_factor

            data.append({
                'date': current_date,
                'nominal_net_worth': float(round(total_nominal, 2)),
                'real_net_worth': float(round(total_real, 2)),
                'pension_total': float(round(pension_total, 2)),
                'real_pension_total': float(round(pension_total / inflation_factor, 2)),
                'asset_total': float(round(asset_total, 2)),
                'real_asset_total': float(round(asset_total / inflation_factor, 2)),
                'physical_asset_total': float(round(physical_asset_total, 2)),
                'real_physical_asset_total': float(round(physical_asset_total / inflation_factor, 2)),
                'real_estate_total': float(round(real_estate_total, 2)),
                'real_real_estate_total': float(round(real_estate_total / inflation_factor, 2)),
                'accumulated_cash': float(round(accumulated_cash, 2)),
                'real_accumulated_cash': float(round(accumulated_cash / inflation_factor, 2)),
                'monthly_income': float(round(monthly_income, 2)),
                'real_monthly_income': float(round(monthly_income / inflation_factor, 2)),
                'monthly_expenses': float(round(monthly_expenses, 2)),
                'real_monthly_expenses': float(round(monthly_expenses / inflation_factor, 2)),
                'monthly_pension_payout': float(round(current_monthly_pension_payout, 2)),
                'real_monthly_pension_payout': float(round(current_monthly_pension_payout / inflation_factor, 2)),
                'real_monthly_pension_payout_fixed': float(round(current_monthly_pension_payout_fixed / inflation_factor, 2)),
                'real_monthly_pension_payout_capital': float(round(current_monthly_pension_payout_capital / inflation_factor, 2)),
                'monthly_pension_contribution': float(round(current_monthly_pension_contribution, 2)),
                'category_breakdown': {k: float(round(v, 2)) for k, v in category_breakdown.items()},
                'income_category_breakdown': {k: float(round(v, 2)) for k, v in income_category_breakdown.items()},
                'one_time_events': events_this_month,
            })
            
        return data
