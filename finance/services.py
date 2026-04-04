import datetime
import math
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from .models import Asset, CashFlowSource, OneTimeEvent, Pension

class SimulationEngine:
    def __init__(self, user, simulation_params=None):
        self.user = user
        self.profile = user.profile
        self.params = simulation_params or {}
        
        # Simulation Parameters from profile or override
        self.inflation_rate = Decimal(str(self.params.get('inflation_rate', self.profile.inflation_rate))) / 100
        self.salary_increase = Decimal(str(self.params.get('salary_increase', self.profile.salary_increase))) / 100
        self.pension_increase = Decimal(str(self.params.get('pension_increase', self.profile.pension_increase))) / 100
        self.investment_return_offset = Decimal(str(self.params.get('investment_return_offset', self.profile.investment_return_offset))) / 100

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
                end_date = self.profile.birth_date + relativedelta(years=self.profile.simulation_max_age)
                diff = relativedelta(end_date, start_date)
                months = diff.years * 12 + diff.months
            else:
                months = 360 # Default 30 years
        
        months = max(1, min(months, 720)) 
        data = []
        
        # Initial State
        assets = list(self.user.assets.all())
        pensions = list(self.user.pensions.all())
        cash_flows = list(self.user.cash_flows.select_related('category').all())
        one_time_events = list(self.user.events.all())

        pensions_state = []
        for p in pensions:
            pensions_state.append({'pension': p, 'balance': p.current_value})
            
        assets_state = []
        for a in assets:
            assets_state.append({'asset': a, 'balance': a.value})
            
        accumulated_cash = Decimal('0.00')

        for i in range(months):
            current_date = start_date + relativedelta(months=i)
            # Inflation calculation relative to Stichtag
            months_from_stichtag = (current_date.year - stichtag.year) * 12 + (current_date.month - stichtag.month)
            year_passed_decimal = Decimal(str(max(0, months_from_stichtag))) / 12

            # 1. Dynamic Pension Contributions and Payouts for this month
            current_monthly_pension_contribution = Decimal('0.00')
            current_monthly_pension_payout = Decimal('0.00')
            
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
                        
                        # Grow Nominal Payout by pension_increase rate annually (step function)
                        payout_val = payout_val * ((1 + self.pension_increase) ** full_years_since_start)
                        current_monthly_pension_payout += payout_val

            # 2. Process Cash Flows (Income/Expenses)
            monthly_income = current_monthly_pension_payout
            monthly_expenses = current_monthly_pension_contribution # Savings count as expense
            category_breakdown = {
                'Sparen': float(current_monthly_pension_contribution)
            }
            income_category_breakdown = {
                'Rente': float(current_monthly_pension_payout)
            } if current_monthly_pension_payout > 0 else {}
            
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
                    rate = (asset.growth_rate / 100) + self.investment_return_offset
                    item['balance'] *= (1 + (rate / 12))
                    if asset.withdrawal_start_date and current_date >= asset.withdrawal_start_date.replace(day=1):
                        item['balance'] = max(Decimal('0'), item['balance'] - asset.withdrawal_amount)
                
                # Apply Pension Growth & Contribution
                for item in pensions_state:
                    pension = item['pension']
                    # Growth applies to current balance
                    rate = (pension.growth_rate / 100)
                    item['balance'] *= (1 + (rate / 12))
                    # Contribution only if before end date
                    if not pension.contribution_end_date or current_date < pension.contribution_end_date.replace(day=1):
                        item['balance'] += pension.monthly_contribution

                # Monthly Savings: monthly_expenses already includes current_monthly_pension_contribution
                monthly_savings = monthly_income - monthly_expenses
                accumulated_cash += (monthly_savings + event_impact)
            
            # Totals
            asset_total = sum(item['balance'] for item in assets_state)
            pension_total = sum(item['balance'] for item in pensions_state)
            total_nominal = asset_total + pension_total + accumulated_cash
            
            # Inflation Factor for Real Value (Purchasing Power)
            inflation_factor = (1 + self.inflation_rate) ** year_passed_decimal
            total_real = total_nominal / inflation_factor

            data.append({
                'date': current_date,
                'nominal_net_worth': float(round(total_nominal, 2)),
                'real_net_worth': float(round(total_real, 2)),
                'pension_total': float(round(pension_total, 2)),
                'real_pension_total': float(round(pension_total / inflation_factor, 2)),
                'asset_total': float(round(asset_total, 2)),
                'real_asset_total': float(round(asset_total / inflation_factor, 2)),
                'accumulated_cash': float(round(accumulated_cash, 2)),
                'real_accumulated_cash': float(round(accumulated_cash / inflation_factor, 2)),
                'monthly_income': float(round(monthly_income, 2)),
                'real_monthly_income': float(round(monthly_income / inflation_factor, 2)),
                'monthly_expenses': float(round(monthly_expenses, 2)),
                'real_monthly_expenses': float(round(monthly_expenses / inflation_factor, 2)),
                'monthly_pension_payout': float(round(current_monthly_pension_payout, 2)),
                'real_monthly_pension_payout': float(round(current_monthly_pension_payout / inflation_factor, 2)),
                'monthly_pension_contribution': float(round(current_monthly_pension_contribution, 2)),
                'category_breakdown': {k: float(round(v, 2)) for k, v in category_breakdown.items()},
                'income_category_breakdown': {k: float(round(v, 2)) for k, v in income_category_breakdown.items()},
                'one_time_events': events_this_month,
            })
            
        return data
