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
        
        if months is None:
            # Calculate total months from start_date until simulation_max_age
            if self.profile.birth_date:
                end_date = self.profile.birth_date + relativedelta(years=self.profile.simulation_max_age)
                # Calculate difference in months
                diff = relativedelta(end_date, start_date)
                months = diff.years * 12 + diff.months
            else:
                months = 360 # Default 30 years
        
        months = max(1, min(months, 720)) # Cap at 60 years or min 1
        data = []
        
        # Initial State
        assets = list(self.user.assets.all())
        pensions = list(self.user.pensions.all())
        cash_flows = list(self.user.cash_flows.all())
        one_time_events = list(self.user.events.all())

        pensions_state = []
        for p in pensions:
            pensions_state.append({'pension': p, 'balance': p.current_value})
            
        assets_state = []
        for a in assets:
            assets_state.append({'asset': a, 'balance': a.value})
            
        # Accumulated cash covers generic monthly savings
        accumulated_cash = Decimal('0.00')

        # Pre-calculate monthly pension contributions to deduct from cashflow
        total_monthly_pension_contribution = sum(p.monthly_contribution for p in pensions)

        today_date = timezone.now().date().replace(day=1)

        for i in range(months):
            current_date = start_date + relativedelta(months=i)
            year_passed = (current_date.year - today_date.year) * 12 + (current_date.month - today_date.month)
            year_passed_decimal = Decimal(str(max(0, year_passed))) / 12

            # 3. Process Cash Flows (Income/Expenses) - Always for all months
            monthly_income = Decimal('0.00')
            monthly_expenses = Decimal('0.00')
            category_breakdown = {}
            income_category_breakdown = {}
            
            for cf in cash_flows:
                if cf.start_date and cf.start_date > current_date:
                    continue
                if cf.end_date and cf.end_date < current_date:
                    continue
                
                amount = cf.value
                
                if cf.is_inflation_adjusted:
                    rate = self.salary_increase if cf.is_income else self.inflation_rate
                    amount = amount * ((1 + rate) ** year_passed_decimal)

                if cf.frequency == 'monthly':
                    val = amount
                elif cf.frequency == 'yearly':
                    val = amount / 12
                else:
                    val = Decimal('0.00') 

                if cf.is_income:
                    monthly_income += val
                    cat_name = cf.category.name if cf.category else "Uncategorized"
                    income_category_breakdown[cat_name] = income_category_breakdown.get(cat_name, Decimal('0')) + val
                else:
                    monthly_expenses += val
                    cat_name = cf.category.name if cf.category else "Uncategorized"
                    category_breakdown[cat_name] = category_breakdown.get(cat_name, Decimal('0')) + val

            # 4. One Time Events - Always for all months
            event_impact = Decimal('0.00')
            events_this_month = []
            for event in one_time_events:
                if event.date.year == current_date.year and event.date.month == current_date.month:
                    event_impact += event.value
                    events_this_month.append({
                        'name': event.name,
                        'description': event.description or '',
                        'date': event.date.isoformat(),
                        'value': float(round(event.value, 2)),
                    })

            # 5. Wealth Accumulation and Growth - START FROM TODAY
            asset_total = Decimal('0.00')
            pension_total = Decimal('0.00')

            if current_date < today_date:
                # History mode: No net worth tracking, only income/expenses
                total_nominal = Decimal('0.00')
                total_real = Decimal('0.00')
            else:
                # Future mode (and Today): Apply growth for months AFTER today
                if current_date > today_date:
                    # Apply Asset Growth & Withdrawals
                    for item in assets_state:
                        asset = item['asset']
                        rate = (asset.growth_rate / 100) + self.investment_return_offset
                        monthly_rate = rate / 12
                        item['balance'] *= (1 + monthly_rate)
                        
                        if asset.withdrawal_start_date and current_date >= asset.withdrawal_start_date:
                            withdrawal = asset.withdrawal_amount
                            item['balance'] = max(Decimal('0'), item['balance'] - withdrawal)
                    
                    # Apply Pension Growth
                    for item in pensions_state:
                        pension = item['pension']
                        rate = (pension.growth_rate / 100)
                        monthly_rate = rate / 12
                        item['balance'] = (item['balance'] + pension.monthly_contribution) * (1 + monthly_rate)

                    # Monthly Savings (Cash)
                    monthly_savings = monthly_income - monthly_expenses - total_monthly_pension_contribution
                    accumulated_cash += (monthly_savings + event_impact)
                
                # Totals for current month (Today or Future)
                asset_total = sum(item['balance'] for item in assets_state)
                pension_total = sum(item['balance'] for item in pensions_state)
                total_nominal = asset_total + pension_total + accumulated_cash
                inflation_factor = (1 + self.inflation_rate) ** year_passed_decimal
                total_real = total_nominal / inflation_factor

            data.append({
                'date': current_date,
                'nominal_net_worth': float(round(total_nominal, 2)),
                'real_net_worth': float(round(total_real, 2)),
                'pension_total': float(round(pension_total, 2)),
                'asset_total': float(round(asset_total, 2)),
                'accumulated_cash': float(round(accumulated_cash, 2)),
                'monthly_income': float(round(monthly_income, 2)),
                'monthly_expenses': float(round(monthly_expenses, 2)),
                'category_breakdown': {k: float(round(v, 2)) for k, v in category_breakdown.items()},
                'income_category_breakdown': {k: float(round(v, 2)) for k, v in income_category_breakdown.items()},
                'one_time_events': events_this_month,
            })
            
        return data
