import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.translation import gettext as _

def calculate_loan_schedule(loan, as_of_date=None, extra_one_time=Decimal('0.00'), extra_one_time_date=None, extra_annual=Decimal('0.00')):
    """
    Computes an exact monthly amortization schedule for a loan,
    supporting:
    - Annuity loans (annuity)
    - Fixed amortization loans (fixed_amortization)
    - Bullet / interest-only loans (bullet)
    Also supports what-if parameters:
    - extra_one_time (additional lump sum)
    - extra_annual (recurring yearly extra prepayment)
    """
    if as_of_date is None:
        as_of_date = timezone.now().date()
        
    start_date = loan.start_date
    balance = Decimal(str(loan.nominal_amount or '0.00'))
    nominal_amount = balance
    annual_rate = Decimal(str(loan.interest_rate or '0.00')) / Decimal('100.00')
    monthly_rate = annual_rate / Decimal('12.00')
    monthly_installment = Decimal(str(loan.monthly_installment or '0.00'))
    loan_type = getattr(loan, 'loan_type', 'annuity') or 'annuity'
    
    # Pre-fetch recorded extra repayments grouped by (year, month)
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
    balance_at_lock_end = None
    
    # For fixed amortization (Tilgungsdarlehen), compute fixed monthly principal
    if loan_type == 'fixed_amortization':
        # If initial_repayment_rate is given, use it; otherwise infer from monthly_installment - interest
        if loan.initial_repayment_rate:
            fixed_monthly_principal = (nominal_amount * (loan.initial_repayment_rate / Decimal('100.00')) / Decimal('12.00')).quantize(Decimal('0.01'))
        else:
            initial_interest = (nominal_amount * monthly_rate).quantize(Decimal('0.01'))
            fixed_monthly_principal = max(Decimal('10.00'), monthly_installment - initial_interest)
    else:
        fixed_monthly_principal = Decimal('0.00')
    
    for month_idx in range(max_months):
        if balance <= Decimal('0.01'):
            if not payoff_date:
                payoff_date = curr_date
            break
            
        # Record balance at interest lock end date
        if loan.interest_lock_end and curr_date.year == loan.interest_lock_end.year and curr_date.month == loan.interest_lock_end.month:
            balance_at_lock_end = balance
            
        interest_month = (balance * monthly_rate).quantize(Decimal('0.01'))
        
        # Check loan end date
        if loan.end_date and curr_date > loan.end_date.replace(day=1):
            if not payoff_date:
                payoff_date = curr_date
            break
            
        # Recorded extra repayments
        extras = extra_repayments.get((curr_date.year, curr_date.month), Decimal('0.00'))
        
        # What-if extra payments (only in future / simulation)
        if curr_date >= as_of_normalized:
            if extra_one_time > 0 and extra_one_time_date:
                if curr_date.year == extra_one_time_date.year and curr_date.month == extra_one_time_date.month:
                    extras += extra_one_time
            elif extra_one_time > 0 and not extra_one_time_date and curr_date == as_of_normalized:
                extras += extra_one_time
                
            if extra_annual > 0 and curr_date.month == 1:
                extras += extra_annual

        # Installment and principal depending on loan type
        if loan_type == 'bullet':
            # Endfälliges Darlehen: only pay interest, principal paid at end
            principal_month = Decimal('0.00')
            installment = interest_month
            if loan.end_date and curr_date.year == loan.end_date.year and curr_date.month == loan.end_date.month:
                principal_month = balance
                installment = interest_month + principal_month
        elif loan_type == 'fixed_amortization':
            # Tilgungsdarlehen: fixed principal + falling interest
            principal_month = min(balance, fixed_monthly_principal)
            installment = interest_month + principal_month
        else:
            # Annuity (default): constant installment
            installment = monthly_installment
            if installment > balance + interest_month:
                installment = balance + interest_month
            principal_month = max(Decimal('0.00'), installment - interest_month)
            
        balance_before = balance
        repayment_total = principal_month + extras
        if repayment_total > balance:
            repayment_total = balance
            extras = max(Decimal('0.00'), repayment_total - principal_month)
            
        balance = max(Decimal('0.00'), balance - repayment_total)
        total_interest_projected += interest_month
        
        # Tracking "as of today"
        if curr_date <= as_of_normalized:
            current_balance = balance
            total_interest_paid_so_far += interest_month
            total_principal_paid_so_far += repayment_total
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

    # Aggregated annual schedule
    annual_schedule = []
    years = sorted(list(set(s['date'].year for s in schedule)))
    for yr in years:
        yr_rows = [s for s in schedule if s['date'].year == yr]
        if yr_rows:
            annual_schedule.append({
                'year': yr,
                'balance_start': yr_rows[0]['balance_start'],
                'total_installment': sum((r['installment'] for r in yr_rows), Decimal('0.00')),
                'total_interest': sum((r['interest'] for r in yr_rows), Decimal('0.00')),
                'total_principal': sum((r['principal'] for r in yr_rows), Decimal('0.00')),
                'total_extra': sum((r['extra'] for r in yr_rows), Decimal('0.00')),
                'balance_end': yr_rows[-1]['balance_end'],
                'is_future': yr >= as_of_date.year,
            })

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

    if balance_at_lock_end is None and loan.interest_lock_end:
        balance_at_lock_end = current_balance

    return {
        'current_balance': current_balance.quantize(Decimal('0.01')),
        'current_interest_portion': current_interest_portion.quantize(Decimal('0.01')),
        'current_principal_portion': current_principal_portion.quantize(Decimal('0.01')),
        'total_interest_paid_so_far': total_interest_paid_so_far.quantize(Decimal('0.01')),
        'total_principal_paid_so_far': total_principal_paid_so_far.quantize(Decimal('0.01')),
        'total_interest_projected': total_interest_projected.quantize(Decimal('0.01')),
        'payoff_date': payoff_date,
        'balance_at_lock_end': (balance_at_lock_end or current_balance).quantize(Decimal('0.01')),
        'calculated_initial_repayment': calc_initial_repayment.quantize(Decimal('0.01')),
        'lock_months_left': lock_months_left,
        'lock_status': lock_status,
        'schedule_count': len(schedule),
        'schedule': schedule,
        'annual_schedule': annual_schedule,
        'schedule_sample': schedule[:12],
    }


def simulate_extra_repayment_savings(loan, extra_one_time=Decimal('0.00'), extra_annual=Decimal('0.00')):
    """
    Simulates what-if impact of extra repayments:
    Returns interest saved, months saved, and new payoff date compared to baseline.
    """
    baseline = calculate_loan_schedule(loan)
    simulated = calculate_loan_schedule(loan, extra_one_time=extra_one_time, extra_annual=extra_annual)
    
    interest_saved = max(Decimal('0.00'), baseline['total_interest_projected'] - simulated['total_interest_projected'])
    months_saved = max(0, baseline['schedule_count'] - simulated['schedule_count'])
    
    return {
        'baseline_interest': baseline['total_interest_projected'],
        'simulated_interest': simulated['total_interest_projected'],
        'interest_saved': interest_saved,
        'baseline_payoff': baseline['payoff_date'],
        'simulated_payoff': simulated['payoff_date'],
        'months_saved': months_saved,
        'years_saved': round(months_saved / 12, 1),
    }


def calculate_refinancing_stress_test(loan):
    """
    Simulates monthly burden changes at refinancing date for various interest rate shocks.
    Scenarios: Current rate, +1.0%, +2.0%, +3.0%, 4.5%, 6.0%
    """
    details = calculate_loan_schedule(loan)
    rem_balance = details['balance_at_lock_end']
    curr_rate = Decimal(str(loan.interest_rate or '3.50'))
    curr_installment = Decimal(str(loan.monthly_installment or '0.00'))
    
    # Assume target payoff in remaining years (or 15 years standard for follow-up financing)
    repay_rate = Decimal(str(loan.initial_repayment_rate or '2.00'))
    if repay_rate <= 0:
        repay_rate = Decimal('2.00')
        
    test_rates = [
        ('current', curr_rate, f"{curr_rate:.2f} % ({_('Aktuell')})"),
        ('plus1', curr_rate + Decimal('1.00'), f"+1,0 % ({curr_rate + 1:.2f} %)"),
        ('plus2', curr_rate + Decimal('2.00'), f"+2,0 % ({curr_rate + 2:.2f} %)"),
        ('plus3', curr_rate + Decimal('3.00'), f"+3,0 % ({curr_rate + 3:.2f} %)"),
        ('fixed_45', Decimal('4.50'), "4,50 %"),
        ('fixed_60', Decimal('6.00'), "6,00 %"),
    ]
    
    scenarios = []
    for code, rate, label in test_rates:
        # Annual annuity = remaining balance * (interest rate + repayment rate) / 100
        annuity_rate = (rate + repay_rate) / Decimal('100.00')
        new_monthly = (rem_balance * annuity_rate / Decimal('12.00')).quantize(Decimal('0.01'))
        diff_monthly = new_monthly - curr_installment
        diff_annual = diff_monthly * Decimal('12.00')
        
        scenarios.append({
            'code': code,
            'rate': rate,
            'label': label,
            'monthly_installment': new_monthly,
            'diff_monthly': diff_monthly,
            'diff_annual': diff_annual,
            'is_increase': diff_monthly > 0,
        })
        
    return {
        'remaining_balance': rem_balance,
        'interest_lock_end': loan.interest_lock_end,
        'current_installment': curr_installment,
        'assumed_repayment_rate': repay_rate,
        'scenarios': scenarios,
    }


def calculate_vacancy_stress_test(real_estate, linked_loans, user_cash_reserve=Decimal('0.00')):
    """
    Simulates rental loss / vacancy stress test for an individual property:
    Calculates ongoing burden without rent, reserve requirements for 3, 6, 12 months,
    and coverage based on available liquid reserves.
    """
    rental_income = Decimal(str(real_estate.rental_income_monthly or '0.00'))
    maintenance = Decimal(str(real_estate.maintenance_costs_monthly or '0.00'))
    ancillary = Decimal(str(real_estate.ancillary_costs_monthly or '0.00'))
    debt_service = sum((Decimal(str(l.monthly_installment or '0.00')) for l in linked_loans), Decimal('0.00'))
    
    # Ongoing cost without rent (property owner pays maintenance + debt service + unallocated ancillary)
    monthly_loss_burden = maintenance + ancillary + debt_service
    
    loss_3m = monthly_loss_burden * 3
    loss_6m = monthly_loss_burden * 6
    loss_12m = monthly_loss_burden * 12
    
    # Months covered by liquid reserves
    months_covered = 999
    if monthly_loss_burden > 0:
        months_covered = round(float(user_cash_reserve / monthly_loss_burden), 1)
        
    return {
        'rental_income': rental_income,
        'monthly_loss_burden': monthly_loss_burden,
        'loss_3m': loss_3m,
        'loss_6m': loss_6m,
        'loss_12m': loss_12m,
        'user_cash_reserve': user_cash_reserve,
        'months_covered': months_covered,
        'is_safe_6m': user_cash_reserve >= loss_6m,
    }


def get_real_estate_overview(user):
    """
    Computes a comprehensive overview of real estates and loans for the user,
    including linked debts, equity, LTV, monthly cashflows, interest-lock alerts,
    and Phase 2 stress-test metrics.
    """
    today = timezone.now().date()
    real_estates = list(user.real_estates.all().order_by('name'))
    user_loans = list(user.loans.select_related('real_estate').prefetch_related('extra_repayments').all().order_by('name'))
    
    # Liquid cash reserve from Asset model (accounts / liquid assets)
    user_cash_reserve = Decimal('0.00')
    for a in user.assets.all():
        user_cash_reserve += Decimal(str(a.value or '0.00'))

    # Precompute all loan details and stress tests
    loan_details_map = {}
    loan_stress_map = {}
    for l in user_loans:
        det = calculate_loan_schedule(l, as_of_date=today)
        loan_details_map[l.id] = det
        loan_stress_map[l.id] = calculate_refinancing_stress_test(l)

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
                'details': det,
                'stress_test': loan_stress_map[l.id],
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
        
        vacancy_stress = calculate_vacancy_stress_test(re, linked, user_cash_reserve)
        
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
            'vacancy_stress': vacancy_stress,
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
                'details': det,
                'stress_test': loan_stress_map[l.id],
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
        'all_loans': [{'loan': l, 'details': loan_details_map[l.id], 'stress_test': loan_stress_map[l.id]} for l in user_loans],
        'total_property_value': total_property_value,
        'total_linked_debt': total_linked_debt,
        'total_unlinked_debt': total_unlinked_debt,
        'total_debt_all': total_debt_all,
        'total_equity_all': total_equity_all,
        'overall_ltv': overall_ltv,
        'total_rental_income': total_rental_income,
        'total_property_cashflow': total_property_cashflow,
        'critical_alerts': critical_alerts,
        'user_cash_reserve': user_cash_reserve,
    }
