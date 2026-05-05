import datetime
import math
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Asset, CashFlowSource, OneTimeEvent, Pension, PhysicalAsset, RealEstate, Loan, LoanExtraRepayment
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
        If a manual start date is set in the profile, it is used as a floor.
        """
        today = datetime.date.today().replace(day=1)
        dates = [today]

        # Check Asset Snapshots (Historical Data)
        from .models import AssetSnapshot
        snapshot_start = AssetSnapshot.objects.filter(user=self.user).order_by('date').first()
        if snapshot_start:
            dates.append(snapshot_start.date)

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

        # Check Loans
        loan_start = self.user.loans.order_by('start_date').first()
        if loan_start:
            dates.append(loan_start.start_date)

        min_date = min(dates)
        
        # If a manual start date is set in the profile, use it as a lower bound (floor)
        if self.profile.simulation_start_date:
            profile_start = self.profile.simulation_start_date.replace(day=1)
            min_date = max(min_date, profile_start)

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
        
        months = max(1, min(months, 1200)) # Increased to 100 years for long histories
        data = []
        
        today = datetime.date.today()
        today_year_start = today.replace(month=1, day=1)
        
        # Initial State
        assets = list(self.user.assets.all())
        pensions = list(self.user.pensions.all())
        cash_flows = list(self.user.cash_flows.select_related('category').all())
        one_time_events = list(self.user.events.all())
        physical_assets = list(self.user.physical_assets.all())
        real_estates = list(self.user.real_estates.all())

        global_re_growth = Decimal(str(self.params.get('real_estate_growth_rate', 0.0)))

        pensions_state = []
        for p in pensions:
            # Initialize with 0 for the past
            pensions_state.append({'pension': p, 'balance': Decimal('0.00')})
            
        assets_state = []
        for a in assets:
            assets_state.append({'asset': a, 'balance': Decimal('0.00')})
            
        physical_assets_state = []
        for pa in physical_assets:
            physical_assets_state.append({'asset': pa, 'balance': Decimal('0.00')})
            
        real_estates_state = []
        for re in real_estates:
            # Initialize with 0 for the past, will be populated by snapshots or future projection
            real_estates_state.append({'asset': re, 'balance': Decimal('0.00')})

        user_loans = list(self.user.loans.prefetch_related('extra_repayments').all())
        loans_state = []
        # 0. Pre-index Events and Repayments for O(1) lookup performance
        events_by_month = {}
        for e in one_time_events:
            key = (e.date.year, e.date.month)
            if key not in events_by_month: events_by_month[key] = []
            events_by_month[key].append(e)
            
        repayments_by_loan_month = {}
        for l in user_loans:
            repayments_by_loan_month[l.id] = {}
            for e in l.extra_repayments.all():
                key = (e.date.year, e.date.month)
                if key not in repayments_by_loan_month[l.id]: repayments_by_loan_month[l.id][key] = []
                repayments_by_loan_month[l.id][key].append(e)
        
        # Pre-index Snapshots for O(1) lookup
        from django.contrib.contenttypes.models import ContentType
        ct_asset = ContentType.objects.get_for_model(Asset).id
        ct_pa = ContentType.objects.get_for_model(PhysicalAsset).id
        ct_re = ContentType.objects.get_for_model(RealEstate).id
        
        snapshots_by_obj = {}
        # Track which (content_type, object_id) we have snapshots for, grouped by month
        snapshots_by_month_type = {} 
        
        for s in self.user.asset_snapshots.all():
            key_obj = (s.content_type_id, s.object_id, s.date.year, s.date.month)
            snapshots_by_obj[key_obj] = s.value
            
            key_month = (s.content_type_id, s.date.year, s.date.month)
            if key_month not in snapshots_by_month_type:
                snapshots_by_month_type[key_month] = {}
            snapshots_by_month_type[key_month][s.object_id] = s.value

        loans_state = []
        for l in user_loans:
            loans_state.append({
                'loan': l, 
                'balance': l.nominal_amount,
                'total_interest_paid': Decimal('0.00')
            })
            
        accumulated_cash = Decimal('0.00')

        today_normalized = today.replace(day=1)
        
        for i in range(months):
            current_date = start_date + relativedelta(months=i)
            is_future = current_date >= today_normalized
            is_today = current_date == today_normalized

            # Standard monthly step for precision
            step_months = 1
            year_passed_decimal_step = Decimal('1') / 12

            # Inflation calculation relative to Today
            months_from_today = (current_date.year - today_normalized.year) * 12 + (current_date.month - today_normalized.month)
            year_passed_decimal = Decimal(str(max(0, months_from_today))) / 12

            # 1. Wealth Accumulation and Growth - Continuous Simulation
            current_monthly_asset_withdrawal = Decimal('0.00')
            
            # Apply Asset Growth & Withdrawals
            if i > 0: # Start growth from the second month
                for item in assets_state:
                    asset = item['asset']
                    # Switch to current value once we hit "Today"
                    if is_today:
                        item['balance'] = asset.value
                        continue

                    if is_future:
                        # Dynamic Interest Rate
                        asset_growth_rate = asset.growth_rate or Decimal('0.00')
                        if asset.interest_teaser_rate is not None and asset.interest_teaser_until and current_date <= asset.interest_teaser_until:
                            asset_growth_rate = asset.interest_teaser_rate
                            
                        rate = (asset_growth_rate / 100) + self.investment_return_offset
                        item['balance'] *= ((1 + (rate / 12)) ** step_months)

                        if asset.withdrawal_start_date and current_date >= asset.withdrawal_start_date.replace(day=1):
                            withdrawal = (asset.withdrawal_amount or Decimal('0.00')) * step_months
                            item['balance'] = max(Decimal('0'), item['balance'] - withdrawal)
                            current_monthly_asset_withdrawal += withdrawal
                    
                    # Numerical Safety
                    item['balance'] = min(item['balance'], Decimal('1e15'))
                
                # Apply Pension Growth & Contribution
                for item in pensions_state:
                    pension = item['pension']
                    # Switch to current value once we hit "Today"
                    if is_today:
                        item['balance'] = pension.current_value
                        continue

                    if is_future:
                        # Growth applies to current balance
                        rate = (pension.growth_rate or Decimal('0.00')) / 100
                        item['balance'] *= ((1 + (rate / 12)) ** step_months)
                        # Contribution only if before end date
                        if not pension.contribution_end_date or current_date < pension.contribution_end_date.replace(day=1):
                            item['balance'] += ((pension.monthly_contribution or Decimal('0.00')) * step_months)
                    
                    # Numerical Safety
                    item['balance'] = min(item['balance'], Decimal('1e15'))

                # Apply Sachwerte Growth
                for item in physical_assets_state:
                    pa = item['asset']
                    # Switch to current value once we hit "Today"
                    if is_today:
                        item['balance'] = pa.value
                        continue

                    # Possession Check (Acquisition & Sale)
                    is_owned = True
                    if pa.acquisition_date and current_date < pa.acquisition_date.replace(day=1):
                        is_owned = False
                    if pa.sale_date and current_date >= pa.sale_date.replace(day=1):
                        is_owned = False
                    if pa.is_sold and i == 0 and (not pa.sale_date or current_date >= pa.sale_date.replace(day=1)):
                        is_owned = False

                    if not is_owned:
                        item['balance'] = Decimal('0.00')
                        continue
                        
                    if is_future:
                        rate = pa.appreciation_rate
                        item['balance'] *= ((1 + (rate / 100 / 12)) ** step_months)
                    
                    # Numerical Safety
                    item['balance'] = min(item['balance'], Decimal('1e15'))
                    
                # Apply Immobilien Growth
                for item in real_estates_state:
                    re = item['asset']
                    # Switch to current value once we hit "Today"
                    if is_today:
                        item['balance'] = re.property_value
                        continue

                    # Possession Check
                    is_owned = True
                    if re.acquisition_date and current_date < re.acquisition_date.replace(day=1):
                        is_owned = False
                    if re.sale_date and current_date >= re.sale_date.replace(day=1):
                        is_owned = False
                    if re.is_sold and i == 0 and (not re.sale_date or current_date >= re.sale_date.replace(day=1)):
                        is_owned = False

                    if not is_owned:
                        item['balance'] = Decimal('0.00')
                        continue

                    if is_future:
                        rate = re.appreciation_rate
                        if rate == 0 and global_re_growth != 0:
                            rate = global_re_growth
                        item['balance'] *= ((1 + (rate / 100 / 12)) ** step_months)
                    
                    # Numerical Safety
                    item['balance'] = min(item['balance'], Decimal('1e15'))

            # 1.1 Override with Snapshots (for past or present)
            from .models import Pension
            ct_pension = ContentType.objects.get_for_model(Pension).id
            
            for item in assets_state:
                key = (ct_asset, item['asset'].id, current_date.year, current_date.month)
                if key in snapshots_by_obj:
                    item['balance'] = snapshots_by_obj[key]

            for item in physical_assets_state:
                key = (ct_pa, item['asset'].id, current_date.year, current_date.month)
                if key in snapshots_by_obj:
                    item['balance'] = snapshots_by_obj[key]

            for item in real_estates_state:
                key = (ct_re, item['asset'].id, current_date.year, current_date.month)
                if key in snapshots_by_obj:
                    item['balance'] = snapshots_by_obj[key]
            
            for item in pensions_state:
                key = (ct_pension, item['pension'].id, current_date.year, current_date.month)
                if key in snapshots_by_obj:
                    item['balance'] = snapshots_by_obj[key]

            # 2. Dynamic Pension Contributions and Payouts for this month
            current_monthly_pension_contribution = Decimal('0.00')
            current_monthly_pension_payout = Decimal('0.00')
            current_monthly_pension_payout_fixed = Decimal('0.00')
            current_monthly_pension_payout_capital = Decimal('0.00')
            
            for p_item in pensions_state:
                p = p_item['pension']
                # Contributions (only if currently paying)
                is_paying = True
                if p.contribution_start_date and current_date < p.contribution_start_date.replace(day=1):
                    is_paying = False
                if p.contribution_end_date and current_date >= p.contribution_end_date.replace(day=1):
                    is_paying = False
                
                if is_paying and p.monthly_contribution and p.monthly_contribution > 0:
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
                            current_monthly_pension_payout += payout_val * step_months
                            
                            # Split by capital base
                            if p.current_value > 0:
                                current_monthly_pension_payout_capital += payout_val * step_months
                            else:
                                current_monthly_pension_payout_fixed += payout_val * step_months

            # 3. Process Cash Flows (Income/Expenses)
            monthly_income = current_monthly_pension_payout + current_monthly_asset_withdrawal
            monthly_expenses = current_monthly_pension_contribution
            category_breakdown = {
                str(_('Sparen')): current_monthly_pension_contribution
            }
            income_category_breakdown = {}
            if current_monthly_asset_withdrawal > 0:
                income_category_breakdown[str(_('Vermögen'))] = current_monthly_asset_withdrawal

            if current_monthly_pension_payout_fixed > 0:
                income_category_breakdown[str(_('Rente'))] = current_monthly_pension_payout_fixed
            if current_monthly_pension_payout_capital > 0:
                cat_name = str(_('Rente'))
                income_category_breakdown[cat_name] = income_category_breakdown.get(cat_name, Decimal('0')) + current_monthly_pension_payout_capital
            
            for cf in cash_flows:
                if cf.start_date and cf.start_date.replace(day=1) > current_date: continue
                if cf.end_date and cf.end_date.replace(day=1) < current_date: continue
                
                amount = cf.value
                if cf.is_inflation_adjusted:
                    rate = self.salary_increase if cf.is_income else self.inflation_rate
                    amount = amount * ((1 + rate) ** year_passed_decimal)

                val = amount if cf.frequency == 'monthly' else amount / 12

                if cf.is_income:
                    monthly_income += val * step_months
                    cat_name = cf.category.name if cf.category else "Uncategorized"
                    income_category_breakdown[cat_name] = income_category_breakdown.get(cat_name, Decimal('0')) + (val * step_months)
                else:
                    monthly_expenses += val * step_months
                    cat_name = cf.category.name if cf.category else "Uncategorized"
                    category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + (val * step_months)

            # Cash flows from PhysicalAssets and RealEstate
            for item in physical_assets_state:
                pa = item['asset']
                # Only process costs if currently owned and costs are > 0
                if item['balance'] > 0 and pa.storage_costs_monthly and pa.storage_costs_monthly > 0:
                    val = pa.storage_costs_monthly
                    monthly_expenses += val
                    cat_name = str(_('Sachwerte'))
                    category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + val
                    
            for item in real_estates_state:
                re = item['asset']
                # Possession Check (Acquisition & Sale)
                is_owned = item['balance'] > 0
                if re.acquisition_date and current_date < re.acquisition_date.replace(day=1):
                    is_owned = False
                if re.sale_date and current_date >= re.sale_date.replace(day=1):
                    is_owned = False
                if re.is_sold and i == 0 and (not re.sale_date or current_date >= re.sale_date.replace(day=1)):
                    is_owned = False

                if is_owned:
                    if re.rental_income_monthly and re.rental_income_monthly > 0:
                        val = re.rental_income_monthly
                        monthly_income += val
                        cat_name = str(_('Immobilien'))
                        income_category_breakdown[cat_name] = income_category_breakdown.get(cat_name, Decimal('0')) + val
                        
                    # Maintenance and ancillary costs
                    costs = (re.maintenance_costs_monthly or Decimal('0')) + (re.ancillary_costs_monthly or Decimal('0'))
                    if costs > 0:
                        monthly_expenses += costs
                        cat_name = str(_('Immobilien'))
                        category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + costs

            # 2.1 Process Loans (Installments and Interest)
            events_this_month = []
            current_monthly_loan_installment = Decimal('0.00')
            for item in loans_state:
                loan = item['loan']
                # Loan only active if after/at start_date and still has balance
                if current_date >= loan.start_date.replace(day=1) and item['balance'] > 0:
                    if not loan.end_date or current_date <= loan.end_date.replace(day=1):
                        installment = loan.monthly_installment
                        # Interest calculation relative to current balance
                        interest = item['balance'] * ((loan.interest_rate or Decimal('0')) / 100 / 12)
                        
                        # Apply installment (part interest, rest principal)
                        if installment > item['balance'] + interest:
                            installment = item['balance'] + interest
                        
                        current_monthly_loan_installment += installment
                        item['total_interest_paid'] += interest
                        cat_name = str(_('Kredit'))
                        category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + installment
                        
                        # Extra repayments lookup (O(1))
                        extras_this_month = sum(e.amount for e in repayments_by_loan_month.get(loan.id, {}).get((current_date.year, current_date.month), []))
                        
                        if i > 0: # Only update balance from second month of core loop
                            reduction = (installment - interest) + extras_this_month
                            item['balance'] = max(Decimal('0'), item['balance'] - reduction)
                        
                        # Numerical Safety: Cap values to prevent JSON-breaking Infinity
                        item['balance'] = min(item['balance'], Decimal('1e15'))

                        # Track Loan Events for Chart Annotations
                        loan_events = []
                        if loan.interest_lock_end and loan.interest_lock_end.year == current_date.year and loan.interest_lock_end.month == current_date.month:
                            loan_events.append({
                                'loan_name': loan.name,
                                'type': 'interest_lock_end',
                                'label': _('Zinsbindung Ende')
                            })
                        
                        # Add extra repayments to events
                        for e in repayments_by_loan_month.get(loan.id, {}).get((current_date.year, current_date.month), []):
                                loan_events.append({
                                    'loan_name': loan.name,
                                    'type': 'extra_repayment',
                                    'amount': float(e.amount),
                                    'label': f"{_('Sondertilgung')} ({float(e.amount):,.2f} €)"
                                })
                        
                        if loan_events:
                            events_this_month.extend(loan_events)
                elif i > 0:
                    # Even if not active yet or finished, we keep current balance at 0 if finished or initial
                    pass

            monthly_expenses += current_monthly_loan_installment

            # 3. One Time Events lookup (O(1))
            event_impact = Decimal('0.00')
            for event in events_by_month.get((current_date.year, current_date.month), []):
                    event_impact += event.value
                    events_this_month.append({
                        'name': event.name, 'description': event.description or '',
                        'date': event.date.isoformat(), 'value': float(round(event.value, 2)),
                    })

            # Monthly Savings only for future months
            monthly_savings = monthly_income - monthly_expenses
            if is_future:
                accumulated_cash += (monthly_savings + event_impact)
            else:
                # In the past, we only respect explicit event impacts if they represent data
                # but usually, we want accumulated_cash to stay at 0 unless snapshots exist
                accumulated_cash = Decimal('0.00')
            
            # Totals calculation
            # Helper to get orphan snapshot totals (snapshots for objects not in the current active list)
            def get_category_total(state_list, ct_id, year, month, attr_name='asset'):
                # 1. Sum up active objects
                total = sum(item['balance'] for item in state_list)
                
                # 2. Add snapshots for objects NOT in the state_list (orphans or old data)
                active_ids = {item[attr_name].id for item in state_list}
                month_snapshots = snapshots_by_month_type.get((ct_id, year, month), {})
                for obj_id, val in month_snapshots.items():
                    if obj_id not in active_ids:
                        total += val
                return total

            asset_total = get_category_total(assets_state, ct_asset, current_date.year, current_date.month)
            pension_total = get_category_total(pensions_state, ct_pension, current_date.year, current_date.month, 'pension')
            physical_asset_total = get_category_total(physical_assets_state, ct_pa, current_date.year, current_date.month)
            real_estate_total = get_category_total(real_estates_state, ct_re, current_date.year, current_date.month)
            loan_total = sum(item['balance'] for item in loans_state)
            
            total_nominal = asset_total + pension_total + accumulated_cash + physical_asset_total + real_estate_total - loan_total
            
            # Final JSON Safety: ensure no NaN or Infinity
            total_nominal = min(max(total_nominal, Decimal('-1e15')), Decimal('1e15'))

            # Inflation Factor for Real Value (Purchasing Power relative to TODAY)
            inflation_factor = Decimal(str(pow(float(1 + self.inflation_rate), float(year_passed_decimal))))
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
                'loan_total': float(round(loan_total, 2)),
                'real_loan_total': float(round(loan_total / inflation_factor, 2)),
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
                'loan_balances': {str(item['loan'].id): float(round(item['balance'], 2)) for item in loans_state},
                'one_time_impact': float(round(event_impact, 2)),
                'one_time_events': events_this_month,
            })
            
            i += step_months
            
        self.loan_interest_totals = {str(item['loan'].id): item['total_interest_paid'] for item in loans_state}
            
        return data
