import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.translation import gettext as _

def calculate_loan_schedule(loan, as_of_date=None):
    """
    Computes an exact monthly amortization schedule for a loan,
    including extra repayments, current balance, interest/principal split,
    and interest-lock countdown.
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()
        
    start_date = loan.start_date
    balance = Decimal(str(loan.nominal_amount or '0.00'))
    nominal_amount = balance
    annual_rate = Decimal(str(loan.interest_rate or '0.00')) / Decimal('100.00')
    monthly_rate = annual_rate / Decimal('12.00')
    monthly_installment = Decimal(str(loan.monthly_installment or '0.00'))
    
    # Pre-fetch extra repayments grouped by (year, month)
    extra_repayments = {}
    for er in loan.extra_repayments.all().order_by('date'):
        key = (er.date.year, er.date.month)
        extra_repayments[key] = extra_repayments.get(key, Decimal('0.00')) + Decimal(str(er.amount))
        
    current_balance = balance
    total_interest_paid_so_far = Decimal('0.00')
    total_principal_paid_so_far = Decimal('0.00')
    current_interest_portion = Decimal('0.00')
    current_principal_portion = Decimal('0.00')
    
    total_interest_projected = Decimal('0.00')
    schedule = []
    
    # Max simulation: up to 50 years (600 months)
    max_months = 600
    curr_date = start_date.replace(day=1)
    as_of_normalized = as_of_date.replace(day=1)
    
    payoff_date = None
    
    for month_idx in range(max_months):
        if balance <= Decimal('0.01'):
            if not payoff_date:
                payoff_date = curr_date
            break
            
        interest_month = (balance * monthly_rate).quantize(Decimal('0.01'))
        
        # Check loan end date
        if loan.end_date and curr_date > loan.end_date.replace(day=1):
            break
            
        extras = extra_repayments.get((curr_date.year, curr_date.month), Decimal('0.00'))
        
        # Installment covers interest + regular principal
        installment = monthly_installment
        if installment > balance + interest_month:
            installment = balance + interest_month
            
        principal_month = max(Decimal('0.00'), installment - interest_month)
        total_payment = installment + extras
        
        balance_before = balance
        balance = max(Decimal('0.00'), balance - principal_month - extras)
        
        total_interest_projected += interest_month
        
        # Tracking "as of today"
        if curr_date <= as_of_normalized:
            current_balance = balance
            total_interest_paid_so_far += interest_month
            total_principal_paid_so_far += (principal_month + extras)
            current_interest_portion = interest_month
            current_principal_portion = principal_month
            
        schedule.append({
            'date': curr_date,
            'balance_start': balance_before,
            'installment': installment,
            'interest': interest_month,
            'principal': principal_month,
            'extra': extras,
            'balance_end': balance,
            'is_future': curr_date > as_of_normalized,
        })
        
        curr_date = curr_date + relativedelta(months=1)
        
    if not payoff_date:
        payoff_date = curr_date

    # Initial repayment rate calculation: (Rate - Zins) / Darlehen * 100
    calc_initial_repayment = Decimal('0.00')
    if nominal_amount > 0 and monthly_installment > 0:
        annual_installment = monthly_installment * Decimal('12.00')
        calc_initial_repayment = max(Decimal('0.00'), (annual_installment / nominal_amount * Decimal('100.00')) - (loan.interest_rate or Decimal('0.00')))
        
    # Interest lock countdown
    lock_months_left = None
    lock_status = 'none' # none, critical, warning, good, expired
    if loan.interest_lock_end:
        months_diff = (loan.interest_lock_end.year - as_of_date.year) * 12 + (loan.interest_lock_end.month - as_of_date.month)
        lock_months_left = months_diff
        if months_diff < 0:
            lock_status = 'expired'
        elif months_diff <= 12:
            lock_status = 'critical' # Red (< 1 year)
        elif months_diff <= 36:
            lock_status = 'warning'  # Yellow (1-3 years)
        else:
            lock_status = 'good'     # Green (> 3 years)

    return {
        'current_balance': current_balance.quantize(Decimal('0.01')),
        'current_interest_portion': current_interest_portion.quantize(Decimal('0.01')),
        'current_principal_portion': current_principal_portion.quantize(Decimal('0.01')),
        'total_interest_paid_so_far': total_interest_paid_so_far.quantize(Decimal('0.01')),
        'total_principal_paid_so_far': total_principal_paid_so_far.quantize(Decimal('0.01')),
        'total_interest_projected': total_interest_projected.quantize(Decimal('0.01')),
        'payoff_date': payoff_date,
        'calculated_initial_repayment': calc_initial_repayment.quantize(Decimal('0.01')),
        'lock_months_left': lock_months_left,
        'lock_status': lock_status,
        'schedule_count': len(schedule),
        'schedule_sample': schedule[:12], # First 12 months for quick preview
    }


def get_real_estate_overview(user):
    """
    Computes a comprehensive overview of real estates and loans for the user,
    including linked debts, equity, LTV, monthly cashflows, and interest-lock alerts.
    """
    today = timezone.now().date()
    real_estates = list(user.real_estates.all().order_by('name'))
    user_loans = list(user.loans.select_related('real_estate').prefetch_related('extra_repayments').all().order_by('name'))
    
    # Precompute all loan details
    loan_details_map = {}
    for l in user_loans:
        loan_details_map[l.id] = calculate_loan_schedule(l, as_of_date=today)

    properties_data = []
    total_property_value = Decimal('0.00')
    total_linked_debt = Decimal('0.00')
    total_rental_income = Decimal('0.00')
    total_property_cashflow = Decimal('0.00')
    
    critical_alerts = []
    
    for re in real_estates:
        # Find loans assigned to this property
        linked = [l for l in user_loans if l.real_estate_id == re.id]
        
        prop_val = Decimal(str(re.property_value or '0.00'))
        total_property_value += prop_val
        
        prop_debt = Decimal('0.00')
        monthly_debt_service = Decimal('0.00')
        nearest_lock_months = None
        nearest_lock_date = None
        
        linked_details = []
        for l in linked:
            det = loan_details_map[l.id]
            bal = det['current_balance']
            prop_debt += bal
            monthly_debt_service += Decimal(str(l.monthly_installment or '0.00'))
            
            # Check interest lock alert
            m_left = det['lock_months_left']
            if m_left is not None:
                if nearest_lock_months is None or m_left < nearest_lock_months:
                    nearest_lock_months = m_left
                    nearest_lock_date = l.interest_lock_end
                    
                if det['lock_status'] in ['critical', 'warning', 'expired']:
                    critical_alerts.append({
                        'loan': l,
                        'real_estate': re,
                        'months_left': m_left,
                        'status': det['lock_status'],
                        'end_date': l.interest_lock_end,
                        'balance': bal
                    })
                    
            linked_details.append({
                'loan': l,
                'details': det
            })
            
        total_linked_debt += prop_debt
        
        equity = max(Decimal('0.00'), prop_val - prop_debt)
        ltv = Decimal('0.00')
        if prop_val > 0:
            ltv = ((prop_debt / prop_val) * Decimal('100.00')).quantize(Decimal('0.1'))
            
        ltv_status = 'excellent' if ltv <= Decimal('60.0') else ('good' if ltv <= Decimal('80.0') else 'elevated')
        
        # Monthly cash flow: Rental income - maintenance - ancillary - loan installment
        rental_income = Decimal(str(re.rental_income_monthly or '0.00'))
        maintenance = Decimal(str(re.maintenance_costs_monthly or '0.00'))
        ancillary = Decimal(str(re.ancillary_costs_monthly or '0.00'))
        total_costs = maintenance + ancillary
        net_cashflow = rental_income - total_costs - monthly_debt_service
        
        total_rental_income += rental_income
        total_property_cashflow += net_cashflow
        
        properties_data.append({
            'real_estate': re,
            'property_value': prop_val,
            'debt': prop_debt,
            'equity': equity,
            'ltv': ltv,
            'ltv_status': ltv_status,
            'rental_income': rental_income,
            'maintenance': maintenance,
            'ancillary': ancillary,
            'monthly_debt_service': monthly_debt_service,
            'net_cashflow': net_cashflow,
            'linked_loans': linked_details,
            'nearest_lock_months': nearest_lock_months,
            'nearest_lock_date': nearest_lock_date,
        })
        
    # Unlinked loans
    unlinked_loans = []
    total_unlinked_debt = Decimal('0.00')
    total_unlinked_service = Decimal('0.00')
    for l in user_loans:
        if not l.real_estate_id:
            det = loan_details_map[l.id]
            bal = det['current_balance']
            total_unlinked_debt += bal
            total_unlinked_service += Decimal(str(l.monthly_installment or '0.00'))
            
            m_left = det['lock_months_left']
            if m_left is not None and det['lock_status'] in ['critical', 'warning', 'expired']:
                critical_alerts.append({
                    'loan': l,
                    'real_estate': None,
                    'months_left': m_left,
                    'status': det['lock_status'],
                    'end_date': l.interest_lock_end,
                    'balance': bal
                })
                
            unlinked_loans.append({
                'loan': l,
                'details': det
            })
            
    total_debt_all = total_linked_debt + total_unlinked_debt
    total_equity_all = max(Decimal('0.00'), total_property_value - total_linked_debt)
    
    overall_ltv = Decimal('0.00')
    if total_property_value > 0:
        overall_ltv = ((total_linked_debt / total_property_value) * Decimal('100.00')).quantize(Decimal('0.1'))

    critical_alerts.sort(key=lambda x: (x['months_left'] if x['months_left'] is not None else 999))

    return {
        'properties': properties_data,
        'unlinked_loans': unlinked_loans,
        'all_loans': [{'loan': l, 'details': loan_details_map[l.id]} for l in user_loans],
        'total_property_value': total_property_value,
        'total_linked_debt': total_linked_debt,
        'total_unlinked_debt': total_unlinked_debt,
        'total_debt_all': total_debt_all,
        'total_equity_all': total_equity_all,
        'overall_ltv': overall_ltv,
        'total_rental_income': total_rental_income,
        'total_property_cashflow': total_property_cashflow,
        'critical_alerts': critical_alerts,
    }
