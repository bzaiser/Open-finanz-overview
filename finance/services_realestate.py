import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.translation import gettext as _
from .models import PropertyComponent, Document

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
        
        # Check loan end date (only stops bullet loans after maturity; annuity/fixed continue until balance <= 0.01)
        if loan_type == 'bullet' and loan.end_date and curr_date > loan.end_date.replace(day=1):
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
            # EndfÃ¤lliges Darlehen: only pay interest, principal paid at end
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
        ('current', curr_rate, f"{curr_rate:.2f} % ({_('Current')})"),
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

    # Calculate reserve metrics for each property
    total_current_reserve = Decimal('0.00')
    total_target_reserve_monthly = Decimal('0.00')
    for p in properties_data:
        re_obj = p['real_estate']
        res_met = calculate_reserve_metrics_for_property(re_obj)
        p['reserve_metrics'] = res_met
        p['components'] = PropertyComponent.objects.filter(real_estate=re_obj).order_by('installation_year')
        total_current_reserve += res_met['current_reserve']
        total_target_reserve_monthly += res_met['peters_monthly']

    components_roadmap = calculate_components_roadmap(user)
    all_loans_data = [{'loan': l, 'details': loan_details_map[l.id], 'stress_test': loan_stress_map[l.id]} for l in user_loans]
    cashflow_calendar = calculate_property_cashflow_calendar(properties_data, all_loans_data)

    # Phase 4: Tax metrics & documents
    total_gross_rent_annual = Decimal('0.00')
    total_loan_interest_annual = Decimal('0.00')
    total_afa_annual = Decimal('0.00')
    total_regular_costs_annual = Decimal('0.00')
    total_invoices_annual = Decimal('0.00')
    total_werbungskosten_annual = Decimal('0.00')
    total_taxable_result_vv = Decimal('0.00')

    for p in properties_data:
        re_obj = p['real_estate']
        linked_l = [item['loan'] for item in p['linked_loans']]
        tax_met = calculate_property_tax_metrics(re_obj, linked_l)
        p['tax_metrics'] = tax_met
        p['documents'] = Document.objects.filter(real_estate=re_obj).order_by('-date')

        if tax_met['is_rental']:
            total_gross_rent_annual += tax_met['annual_rental_income']
            total_loan_interest_annual += tax_met['annual_interest']
            total_afa_annual += tax_met['annual_afa']
            total_regular_costs_annual += tax_met['annual_regular_costs']
            total_invoices_annual += tax_met['annual_invoice_costs']
            total_werbungskosten_annual += tax_met['total_werbungskosten']
            total_taxable_result_vv += tax_met['taxable_result']

    portfolio_tax = {
        'total_gross_rent_annual': total_gross_rent_annual,
        'total_loan_interest_annual': total_loan_interest_annual,
        'total_afa_annual': total_afa_annual,
        'total_regular_costs_annual': total_regular_costs_annual,
        'total_invoices_annual': total_invoices_annual,
        'total_werbungskosten_annual': total_werbungskosten_annual,
        'total_taxable_result_vv': total_taxable_result_vv,
        'estimated_tax_impact': (abs(total_taxable_result_vv) * Decimal('0.35')).quantize(Decimal('0.01')),
        'is_tax_saving': total_taxable_result_vv < Decimal('0.00'),
    }

    documents_data = get_property_documents_data(user)

    portfolio_reserves = {
        'total_current_reserve': total_current_reserve,
        'total_target_monthly': total_target_reserve_monthly,
        'reserve_vs_5yr_demand': total_current_reserve - components_roadmap['capital_5_years'],
        'reserve_vs_10yr_demand': total_current_reserve - components_roadmap['capital_10_years'],
    }

    return {
        'properties': properties_data,
        'unlinked_loans': unlinked_loans,
        'all_loans': all_loans_data,
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
        'components_roadmap': components_roadmap,
        'portfolio_reserves': portfolio_reserves,
        'cashflow_calendar': cashflow_calendar,
        'portfolio_tax': portfolio_tax,
        'documents_data': documents_data,
    }


def calculate_reserve_metrics_for_property(re):
    """
    Computes maintenance reserve recommendations:
    - Peterssche Formel: (Property value * 70% * 1.5) / 80 / 12
    - § 28 Abs. 2 II. BV: depending on building age and living space
    For unbuilt land ('land'), no building maintenance reserve is recommended.
    """
    current_year = timezone.now().year
    prop_val = Decimal(str(re.property_value or '0.00'))
    living_sqm = Decimal(str(re.living_space_sqm or '0.00')) if re.living_space_sqm else Decimal('0.00')
    is_land = getattr(re, 'property_type', 'apartment') == 'land'
    current_reserve = Decimal(str(re.current_maintenance_reserve or '0.00'))
    actual_monthly = Decimal(str(re.monthly_maintenance_allocation or re.maintenance_costs_monthly or '0.00'))

    if is_land:
        return {
            'is_land': True,
            'building_age': None,
            'living_space_sqm': living_sqm,
            'current_reserve': current_reserve,
            'actual_monthly_allocation': actual_monthly,
            'peters_annual': Decimal('0.00'),
            'peters_monthly': Decimal('0.00'),
            'iibv_rate_sqm': Decimal('0.00'),
            'iibv_annual': Decimal('0.00'),
            'iibv_monthly': Decimal('0.00'),
            'monthly_gap_peters': actual_monthly,
            'is_sufficient': True,
        }

    const_year = re.construction_year or (current_year - 30)
    building_age = max(0, current_year - const_year)

    # Peterssche Formel
    # Building share approx 70% of total property value
    building_value = prop_val * Decimal('0.70')
    peters_annual = (building_value * Decimal('1.5')) / Decimal('80.0')
    peters_monthly = (peters_annual / Decimal('12.0')).quantize(Decimal('0.01'))

    # II. BV: Rate per m² / year based on age
    if building_age < 22:
        iibv_rate_sqm = Decimal('8.50')
    elif building_age <= 32:
        iibv_rate_sqm = Decimal('10.50')
    else:
        iibv_rate_sqm = Decimal('13.00')

    if living_sqm > 0:
        iibv_annual = (living_sqm * iibv_rate_sqm).quantize(Decimal('0.01'))
    else:
        # Fallback if sqm not specified: derive from peters formula
        iibv_annual = peters_annual

    iibv_monthly = (iibv_annual / Decimal('12.0')).quantize(Decimal('0.01'))

    # Gap compared to Peterssche Formel
    monthly_gap_peters = actual_monthly - peters_monthly
    is_sufficient = monthly_gap_peters >= Decimal('0.00')

    return {
        'is_land': False,
        'building_age': building_age,
        'living_space_sqm': living_sqm,
        'current_reserve': current_reserve,
        'actual_monthly_allocation': actual_monthly,
        'peters_annual': peters_annual.quantize(Decimal('0.01')),
        'peters_monthly': peters_monthly,
        'iibv_rate_sqm': iibv_rate_sqm,
        'iibv_annual': iibv_annual,
        'iibv_monthly': iibv_monthly,
        'monthly_gap_peters': monthly_gap_peters,
        'is_sufficient': is_sufficient,
    }


def calculate_components_roadmap(user):
    """
    Groups all property components for a user into time horizons:
    - Overdue / Critical (<= 0 years or condition == critical)
    - 1-5 Years
    - 6-10 Years
    - Long-term (> 10 years)
    Calculates total capital demand per period.
    """
    components = PropertyComponent.objects.filter(real_estate__user=user).select_related('real_estate').order_by('installation_year')
    current_year = timezone.now().year

    overdue = []
    due_1_5 = []
    due_6_10 = []
    long_term = []

    capital_overdue = Decimal('0.00')
    capital_5_years = Decimal('0.00')
    capital_10_years = Decimal('0.00')
    capital_total = Decimal('0.00')

    all_components = []

    for comp in components:
        rem_years = comp.remaining_years
        cost = Decimal(str(comp.estimated_cost or '0.00'))
        capital_total += cost

        comp_data = {
            'obj': comp,
            'remaining_years': rem_years,
            'replacement_year': comp.replacement_year,
            'cost': cost,
        }
        all_components.append(comp_data)

        if rem_years <= 0 or comp.condition == 'critical':
            overdue.append(comp_data)
            capital_overdue += cost
            capital_5_years += cost
            capital_10_years += cost
        elif rem_years <= 5:
            due_1_5.append(comp_data)
            capital_5_years += cost
            capital_10_years += cost
        elif rem_years <= 10:
            due_6_10.append(comp_data)
            capital_10_years += cost
        else:
            long_term.append(comp_data)

    return {
        'all_components': all_components,
        'overdue': overdue,
        'due_1_5': due_1_5,
        'due_6_10': due_6_10,
        'long_term': long_term,
        'capital_overdue': capital_overdue,
        'capital_5_years': capital_5_years,
        'capital_10_years': capital_10_years,
        'capital_total': capital_total,
        'count_overdue': len(overdue),
        'count_total': len(all_components),
    }


def calculate_property_cashflow_calendar(user_properties, all_loans):
    """
    Generates a 12-month calendar projection for real estate cash flows without artificial flattening:
    - Real periodicity:
      * Base monthly operating costs (Hausgeld / laufende Umlagen = 70% of ancillary)
      * Quarterly Property Tax (Grundsteuer Q1-Q4 in Feb, May, Aug, Nov = 20% of annual ancillary / 4)
      * Annual Building Insurance (Gebäudeversicherung in Jan = 10% of annual ancillary)
      * Monthly rental income
      * Monthly loan installments per loan
      * Monthly maintenance allocation / reserve
    - Itemized breakdown for every month (drilldown per property & loan)
    - Monthly net cashflow & cumulative annual curve
    """
    month_names = [
        _('Jan'), _('Feb'), _('Mar'), _('Apr'), _('May'), _('Jun'),
        _('Jul'), _('Aug'), _('Sep'), _('Oct'), _('Nov'), _('Dec')
    ]
    
    calendar_months = []
    current_year = timezone.now().year

    # Map loans by property
    loans_by_prop = {}
    for l_data in all_loans:
        loan = l_data['loan']
        re_id = loan.real_estate_id
        loans_by_prop.setdefault(re_id, []).append(l_data)

    # Expiries this year
    expiries_by_month = {}
    for l_data in all_loans:
        loan = l_data['loan']
        if loan.interest_lock_end and loan.interest_lock_end.year == current_year:
            m = loan.interest_lock_end.month
            expiries_by_month.setdefault(m, []).append(loan)

    cumulative_cashflow = Decimal('0.00')

    for i, name in enumerate(month_names, 1):
        month_rent = Decimal('0.00')
        month_debt = Decimal('0.00')
        month_maint = Decimal('0.00')
        month_anc = Decimal('0.00')

        items_inflow = []
        items_outflow = []
        events = []

        # 1. Properties: Rental income, maintenance, and realistic unflattened ancillary
        for p in user_properties:
            re = p['real_estate']
            rent = Decimal(str(p['rental_income'] or '0.00'))
            maint = Decimal(str(p['maintenance'] or '0.00'))
            anc_monthly_budget = Decimal(str(p['ancillary'] or '0.00'))

            if rent > 0:
                month_rent += rent
                items_inflow.append({
                    'title': _('Rental income %(tenant)s') % {'tenant': f'({re.name})'},
                    'property_name': re.name,
                    'category': _('Rent'),
                    'amount': rent,
                    'is_income': True
                })

            if maint > 0:
                month_maint += maint
                items_outflow.append({
                    'title': _('Maintenance reserve allocation (%(name)s)') % {'name': re.name},
                    'property_name': re.name,
                    'category': _('Maintenance'),
                    'amount': maint,
                    'is_income': False
                })

            # Unflattened ancillary structure:
            # 70% continuous monthly (Hausgeld / upkeep)
            # 10% annual building insurance in January (Month 1)
            # 20% quarterly property tax in Feb(2), May(5), Aug(8), Nov(11) -> 5% each quarter
            if anc_monthly_budget > 0:
                base_monthly = (anc_monthly_budget * Decimal('0.70')).quantize(Decimal('0.01'))
                month_anc += base_monthly
                items_outflow.append({
                    'title': _('Ongoing building charges / utilities (%(name)s)') % {'name': re.name},
                    'property_name': re.name,
                    'category': _('Ancillary'),
                    'amount': base_monthly,
                    'is_income': False
                })

                if i == 1:
                    insurance_amt = (anc_monthly_budget * Decimal('12.0') * Decimal('0.10')).quantize(Decimal('0.01'))
                    if insurance_amt > 0:
                        month_anc += insurance_amt
                        items_outflow.append({
                            'title': _('Building insurance annual premium (%(name)s)') % {'name': re.name},
                            'property_name': re.name,
                            'category': _('Insurance'),
                            'amount': insurance_amt,
                            'is_income': False
                        })
                        events.append({
                            'type': 'insurance',
                            'badge_class': 'bg-info bg-opacity-10 text-info',
                            'icon': 'bi-shield-check',
                            'title': _('Building Insurance: %(name)s (%(amt)s €)') % {'name': re.name, 'amt': insurance_amt}
                        })

                if i in (2, 5, 8, 11):
                    q_num = (i // 3) + 1
                    quarterly_tax = (anc_monthly_budget * Decimal('12.0') * Decimal('0.05')).quantize(Decimal('0.01'))
                    if quarterly_tax > 0:
                        month_anc += quarterly_tax
                        items_outflow.append({
                            'title': _('Property tax Grundsteuer Q%(q)s (%(name)s)') % {'q': q_num, 'name': re.name},
                            'property_name': re.name,
                            'category': _('Tax'),
                            'amount': quarterly_tax,
                            'is_income': False
                        })
                        events.append({
                            'type': 'tax',
                            'badge_class': 'bg-primary bg-opacity-10 text-primary',
                            'icon': 'bi-receipt',
                            'title': _('Grundsteuer Q%(q)s: %(name)s (%(amt)s €)') % {'q': q_num, 'name': re.name, 'amt': quarterly_tax}
                        })

        # 2. Loans: Monthly installment per loan
        for l_data in all_loans:
            loan = l_data['loan']
            inst = Decimal(str(loan.monthly_installment or '0.00'))
            if inst > 0:
                month_debt += inst
                re_name = loan.real_estate.name if loan.real_estate else _('Unassigned')
                items_outflow.append({
                    'title': f'{loan.name} ({loan.provider})',
                    'property_name': re_name,
                    'category': _('Debt Service'),
                    'amount': inst,
                    'is_income': False
                })

        # Interest lock expiries
        if i in expiries_by_month:
            for l_obj in expiries_by_month[i]:
                events.append({
                    'type': 'loan',
                    'badge_class': 'bg-warning bg-opacity-25 text-warning-emphasis',
                    'icon': 'bi-alarm-fill',
                    'title': _('Interest Lock Ends: %(name)s') % {'name': l_obj.name}
                })

        total_exp = month_debt + month_maint + month_anc
        net = month_rent - total_exp
        cumulative_cashflow += net

        calendar_months.append({
            'month_num': i,
            'month_name': name,
            'rental_income': month_rent,
            'debt_service': month_debt,
            'maintenance': month_maint,
            'ancillary': month_anc,
            'total_expenses': total_exp,
            'net_cashflow': net,
            'cumulative_cashflow': cumulative_cashflow,
            'items_inflow': items_inflow,
            'items_outflow': items_outflow,
            'total_items_count': len(items_inflow) + len(items_outflow),
            'events': events,
        })

    annual_totals = {
        'total_rent': sum(m['rental_income'] for m in calendar_months),
        'total_debt': sum(m['debt_service'] for m in calendar_months),
        'total_maintenance': sum(m['maintenance'] for m in calendar_months),
        'total_ancillary': sum(m['ancillary'] for m in calendar_months),
        'total_expenses': sum(m['total_expenses'] for m in calendar_months),
        'total_net': sum(m['net_cashflow'] for m in calendar_months),
    }

    return {
        'months': calendar_months,
        'annual_totals': annual_totals,
        'chart_labels': [m['month_name'] for m in calendar_months],
        'chart_rent': [float(m['rental_income']) for m in calendar_months],
        'chart_debt': [float(m['debt_service']) for m in calendar_months],
        'chart_expenses': [float(m['total_expenses']) for m in calendar_months],
        'chart_net': [float(m['net_cashflow']) for m in calendar_months],
        'chart_cumulative': [float(m['cumulative_cashflow']) for m in calendar_months],
    }


def calculate_property_tax_metrics(re, linked_loans, year=None):
    """
    Computes tax metrics (Anlage V preparation):
    - Annual gross rental income
    - Deductions (Werbungskosten):
      1. Mortgage interest (Schuldzinsen)
      2. Building depreciation (AfA: linear % of building value)
      3. Operating & regular maintenance expenses
      4. Craftsman / renovation invoices uploaded for this property
    - Net taxable result from rental & leasing (Einkünfte aus V+V)
    - Estimated tax impact (at assumed 35% personal tax rate)
    """
    if year is None:
        year = timezone.now().year

    prop_val = Decimal(str(re.property_value or '0.00'))
    is_land = getattr(re, 'property_type', 'apartment') == 'land'
    if is_land:
        bld_share = Decimal('0.00')
        depr_rate = Decimal('0.00')
    else:
        raw_bld_share = re.building_share_percent if re.building_share_percent is not None else Decimal('70.0')
        raw_depr_rate = re.depreciation_rate_percent if re.depreciation_rate_percent is not None else Decimal('2.0')
        bld_share = Decimal(str(raw_bld_share)) / Decimal('100.0')
        depr_rate = Decimal(str(raw_depr_rate)) / Decimal('100.0')
    is_rental = getattr(re, 'is_rental_property', True)

    # 1. Rental income
    rental_monthly = Decimal(str(re.rental_income_monthly or '0.00'))
    annual_rental_income = (rental_monthly * Decimal('12.0')).quantize(Decimal('0.01'))

    # 2. Mortgage interest for the current year
    annual_interest = Decimal('0.00')
    for l in linked_loans:
        sched = calculate_loan_schedule(l)
        for row in sched['annual_schedule']:
            if row['year'] == year:
                annual_interest += row['total_interest']
                break

    # 3. Building AfA
    building_value = (prop_val * bld_share).quantize(Decimal('0.01'))
    annual_afa = (building_value * depr_rate).quantize(Decimal('0.01'))

    # 4. Operating and maintenance costs
    maint_monthly = Decimal(str(re.maintenance_costs_monthly or '0.00'))
    anc_monthly = Decimal(str(re.ancillary_costs_monthly or '0.00'))
    annual_regular_costs = ((maint_monthly + anc_monthly) * Decimal('12.0')).quantize(Decimal('0.01'))

    # 5. Direct maintenance invoices uploaded for this property
    doc_invoices = Document.objects.filter(
        real_estate=re,
        category='maintenance_invoice',
        date__year=year
    )
    annual_invoice_costs = sum((Decimal(str(d.amount or '0.00')) for d in doc_invoices), Decimal('0.00'))

    total_werbungskosten = annual_interest + annual_afa + annual_regular_costs + annual_invoice_costs
    taxable_result = (annual_rental_income - total_werbungskosten).quantize(Decimal('0.01'))

    assumed_tax_rate = Decimal('0.35')
    tax_impact = (abs(taxable_result) * assumed_tax_rate).quantize(Decimal('0.01'))
    # If result is negative (tax loss), it generates tax savings
    is_tax_saving = taxable_result < Decimal('0.00')

    return {
        'year': year,
        'is_rental': is_rental,
        'building_value': building_value,
        'annual_rental_income': annual_rental_income,
        'annual_interest': annual_interest,
        'annual_afa': annual_afa,
        'annual_regular_costs': annual_regular_costs,
        'annual_invoice_costs': annual_invoice_costs,
        'total_werbungskosten': total_werbungskosten,
        'taxable_result': taxable_result,
        'tax_impact': tax_impact,
        'is_tax_saving': is_tax_saving,
    }


def get_property_documents_data(user):
    """
    Retrieves all real estate & loan documents for the user.
    """
    docs = (
        Document.objects.filter(user=user, domain__in=['real_estate', 'loan'])
        .select_related('real_estate', 'loan')
        .order_by('-date', '-uploaded_at')
    )
    total_invoices_amount = sum((Decimal(str(d.amount or '0.00')) for d in docs if d.amount), Decimal('0.00'))
    
    return {
        'documents': docs,
        'total_count': docs.count(),
        'total_invoices_amount': total_invoices_amount,
    }
