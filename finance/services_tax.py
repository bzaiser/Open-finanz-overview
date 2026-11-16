import datetime
import re
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext as _


def _parse_de_decimal(raw_str):
    if not raw_str:
        return None
    s = str(raw_str).strip()
    is_neg = False
    if s.startswith('-') or s.endswith('-') or 'minus' in s.lower():
        is_neg = True
    s = re.sub(r'[^0-9,.]', '', s)
    if not s:
        return None
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')
    elif '.' in s:
        parts = s.split('.')
        if len(parts[-1]) == 3:
            s = s.replace('.', '')
    try:
        val = Decimal(s).quantize(Decimal('0.01'))
        return -val if is_neg else val
    except Exception:
        return None


def parse_tax_assessment_pdf(file_obj, filename=None):
    """
    Deterministic, AI-free parser for German Einkommensteuerbescheide (ELSTER / Finanzamt / WISO / DATEV).
    Extracts year, assessment_type, gross_income, deductible_expenses, rental_income_taxable,
    taxable_income_zve, assessed_tax_total, prepaid_tax, and refund_or_payment.
    """
    from .services_documents import extract_document_text

    text = extract_document_text(file_obj, filename=filename, max_chars=50000) or ""
    if not text.strip():
        return {
            'ok': False,
            'message': str(_('Keine lesbare Textebene im PDF gefunden (evtl. reiner Bild-Scan). Bitte Werte manuell eintragen.')),
            'found_fields': [],
            'data': {},
        }

    found_fields = []
    current_year = timezone.localdate().year
    data = {
        'year': current_year - 1,
        'assessment_type': 'splitting',
        'gross_income': Decimal('0.00'),
        'deductible_expenses': Decimal('0.00'),
        'rental_income_taxable': Decimal('0.00'),
        'taxable_income_zve': Decimal('0.00'),
        'assessed_tax_total': Decimal('0.00'),
        'prepaid_tax': Decimal('0.00'),
        'refund_or_payment': Decimal('0.00'),
    }

    # 1. Year detection
    year_patterns = [
        r'(?:Bescheid|Steuerbescheid)\s+f[üu]r\s+(20[123]\d)',
        r'Einkommensteuer(?:bescheid)?\s+(?:f[üu]r\s+)?(20[123]\d)',
        r'Veranlagungszeitraum\s*:?\s*(20[123]\d)',
        r'Steuerjahr\s*:?\s*(20[123]\d)',
    ]
    for pat in year_patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            y = int(m.group(1))
            if 2010 <= y <= current_year + 1:
                data['year'] = y
                found_fields.append('year')
                break

    # 2. Assessment type (Splitting vs. Grundtarif)
    low_text = text.lower()
    if any(k in low_text for k in ('splittingtarif', 'splittingverfahren', 'zusammenveranlagung', 'ehegatten')):
        data['assessment_type'] = 'splitting'
        found_fields.append('assessment_type')
    elif any(k in low_text for k in ('grundtarif', 'einzelveranlagung', 'grundtabelle')):
        data['assessment_type'] = 'single'
        found_fields.append('assessment_type')

    def _find_amount(patterns):
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
            if m:
                val = _parse_de_decimal(m.group(1))
                if val is not None:
                    return val
        return None

    # 3. Zu versteuerndes Einkommen (zvE)
    zve = _find_amount([
        r'zu\s+versteuerndes\s+Einkommen[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
        r'Zu\s+versteuerndes\s+Einkommen\s*\(zvE\)[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
    ])
    if zve is not None and zve >= 0:
        data['taxable_income_zve'] = zve
        found_fields.append('taxable_income_zve')

    # 4. Gesamtbetrag / Summe der Einkünfte / Bruttoarbeitslohn
    gross = _find_amount([
        r'Gesamtbetrag\s+der\s+Eink[üu]nfte[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
        r'Summe\s+der\s+Eink[üu]nfte[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
        r'Bruttoarbeitslohn[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
    ])
    if gross is not None and gross >= 0:
        data['gross_income'] = gross
        found_fields.append('gross_income')

    # 5. Einkünfte aus Vermietung und Verpachtung (Anlage V)
    rental = _find_amount([
        r'Eink[üu]nfte\s+aus\s+Vermietung\s+und\s+Verpachtung[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
        r'Vermietung\s+und\s+Verpachtung[^\n0-9\-]*([\-]?\d[\d\.,]*[\-]?)',
    ])
    if rental is not None:
        data['rental_income_taxable'] = rental
        found_fields.append('rental_income_taxable')

    # 6. Festgesetzte Einkommensteuer (+ Soli + Kirchensteuer)
    est = _find_amount([
        r'Festgesetzte\s+Einkommensteuer[^\n0-9\-]*(\d[\d\.,]*)',
        r'festgesetzte\s+Steuer(?:n)?\s+gesamt[^\n0-9\-]*(\d[\d\.,]*)',
        r'tarifliche\s+Einkommensteuer[^\n0-9\-]*(\d[\d\.,]*)',
    ])
    soli = _find_amount([
        r'Solidarit[äa]tszuschlag[^\n0-9\-]*(\d[\d\.,]*)',
    ]) or Decimal('0.00')
    kist = _find_amount([
        r'Kirchensteuer[^\n0-9\-]*(\d[\d\.,]*)',
    ]) or Decimal('0.00')

    if est is not None and est >= 0:
        total_tax = est + (soli if soli < est else Decimal('0.00')) + (kist if kist < est else Decimal('0.00'))
        data['assessed_tax_total'] = total_tax.quantize(Decimal('0.01'))
        found_fields.append('assessed_tax_total')

    # 7. Bereits gezahlte Lohnsteuer / Vorauszahlungen
    prepaid = _find_amount([
        r'Steuerabzug\s+vom\s+Lohn[^\n0-9\-]*(\d[\d\.,]*)',
        r'Bereits\s+getilgt[^\n0-9\-]*(\d[\d\.,]*)',
        r'anzurechnende\s+Steuern[^\n0-9\-]*(\d[\d\.,]*)',
        r'Gezahlte\s+Vorauszahlungen[^\n0-9\-]*(\d[\d\.,]*)',
    ])
    if prepaid is not None and prepaid >= 0:
        data['prepaid_tax'] = prepaid
        found_fields.append('prepaid_tax')

    # 8. Erstattung / Nachzahlung
    refund = _find_amount([
        r'(?:wird\s+erstattet|Erstattungsbetrag|Guthaben)[^\n0-9\-]*(\d[\d\.,]*)',
    ])
    payment = _find_amount([
        r'(?:Bitte\s+zahlen\s+Sie|Nachzahlung|Restbetrag\s+bis)[^\n0-9\-]*(\d[\d\.,]*)',
    ])
    if refund is not None:
        data['refund_or_payment'] = abs(refund)
        found_fields.append('refund_or_payment')
    elif payment is not None:
        data['refund_or_payment'] = -abs(payment)
        found_fields.append('refund_or_payment')
    elif 'assessed_tax_total' in found_fields and 'prepaid_tax' in found_fields:
        data['refund_or_payment'] = (data['prepaid_tax'] - data['assessed_tax_total']).quantize(Decimal('0.01'))
        found_fields.append('refund_or_payment')

    # 9. Deductible expenses (derived if gross > zvE)
    if data['gross_income'] > data['taxable_income_zve'] and data['taxable_income_zve'] > 0:
        data['deductible_expenses'] = (data['gross_income'] - data['taxable_income_zve']).quantize(Decimal('0.01'))
        found_fields.append('deductible_expenses')

    serialized = {
        k: (f"{v:.2f}" if isinstance(v, Decimal) else v)
        for k, v in data.items()
    }
    return {
        'ok': len(found_fields) > 0,
        'found_fields': found_fields,
        'data': serialized,
        'message': (
            str(_(f"{len(found_fields)} Steuer-Kennzahlen automatisch aus dem PDF erkannt. Bitte kurz prüfen und speichern."))
            if found_fields else
            str(_("Im PDF wurden keine Standard-Steuerbescheid-Felder erkannt. Bitte Werte manuell prüfen."))
        ),
    }


def _tariff_32a_single(zve_float):
    """
    German § 32a EStG base tariff (Grundtarif) for a given taxable income (zvE).
    """
    x = max(0.0, float(zve_float))
    if x <= 12096.0:
        return 0.0
    elif x <= 17443.0:
        y = (x - 12096.0) / 10000.0
        return (932.30 * y + 1400.0) * y
    elif x <= 68480.0:
        z = (x - 17443.0) / 10000.0
        return (176.64 * z + 2397.0) * z + 1015.13
    elif x <= 277825.0:
        return 0.42 * x - 10911.92
    else:
        return 0.45 * x - 19246.67


def calculate_german_income_tax(zve, splitting=False, church_tax_rate=0.0, calibration_multiplier=1.0):
    """
    Calculates German Einkommensteuer + Solidaritätszuschlag + Kirchensteuer,
    plus effective and marginal tax rates.
    """
    zve_f = max(0.0, float(zve or 0.0))
    if zve_f <= 0.0:
        return {
            'income_tax': Decimal('0.00'),
            'soli': Decimal('0.00'),
            'church_tax': Decimal('0.00'),
            'total_tax': Decimal('0.00'),
            'effective_rate': 0.0,
            'marginal_rate': 0.0,
        }

    if splitting:
        est = 2.0 * _tariff_32a_single(zve_f / 2.0)
        est_plus = 2.0 * _tariff_32a_single((zve_f + 1000.0) / 2.0)
        soli_freigrenze = 36260.0
    else:
        est = _tariff_32a_single(zve_f)
        est_plus = _tariff_32a_single(zve_f + 1000.0)
        soli_freigrenze = 18130.0

    est *= float(calibration_multiplier or 1.0)
    est_plus *= float(calibration_multiplier or 1.0)

    # Solidaritätszuschlag (with Freigrenze & Milderungszone 11.9%)
    if est <= soli_freigrenze:
        soli = 0.0
    else:
        soli = min(est * 0.055, (est - soli_freigrenze) * 0.119)

    # Kirchensteuer
    kist_rate = max(0.0, float(church_tax_rate or 0.0)) / 100.0
    kist = est * kist_rate

    total = est + soli + kist
    # Marginal tax rate for +1,000 € additional income (including church tax & soli effect)
    marginal_est = (est_plus - est) / 1000.0
    marginal_total = marginal_est * (1.0 + kist_rate + (0.055 if est > soli_freigrenze else 0.0)) * 100.0
    marginal_total = min(50.0, max(0.0, marginal_total))
    effective_rate = min(50.0, max(0.0, (total / zve_f) * 100.0))

    return {
        'income_tax': Decimal(str(round(est, 2))),
        'soli': Decimal(str(round(soli, 2))),
        'church_tax': Decimal(str(round(kist, 2))),
        'total_tax': Decimal(str(round(total, 2))),
        'effective_rate': round(effective_rate, 1),
        'marginal_rate': round(marginal_total, 1),
    }


def _drv_taxable_cohort_share(retirement_year):
    """
    § 22 Nr. 1 S. 3 Buchst. a Doppelbuchst. aa EStG (Wachstumschancengesetz):
    2023 = 82.5%, +0.5% per year until 2058 = 100%.
    """
    if retirement_year <= 2005:
        return 0.50
    if retirement_year <= 2020:
        return 0.50 + (retirement_year - 2005) * 0.02
    if retirement_year <= 2022:
        return 0.80 + (retirement_year - 2020) * 0.01
    if retirement_year >= 2058:
        return 1.00
    return min(1.00, 0.825 + (retirement_year - 2023) * 0.005)


def calculate_holistic_tax_cockpit(user, portfolio_tax_vv=None, rental_objects_metrics=None):
    """
    Builds the complete Holistic Tax Cockpit:
    1. Calibration from historical TaxAssessment records (learned deductions, real marginal & effective rates)
    2. Current year holistic tax breakdown across all income pillars & life situation
    3. 30-year life-phase projection (working -> children independent -> retirement -> loan interest decline)
    4. Actionable life-phase tax hints (non-binding educational orientation)
    """
    from .models import Asset, CashFlowSource, Loan, Pension, RealEstate, TaxAssessment

    today = timezone.localdate()
    current_year = today.year
    profile = getattr(user, 'profile', None)
    situation = getattr(profile, 'household_situation', 'standard') if profile else 'standard'
    has_partner = bool(profile and (profile.partner_name or (profile.display_name and '&' in profile.display_name)))

    tax_mode = getattr(profile, 'tax_assessment_mode', 'auto') if profile else 'auto'
    if tax_mode == 'splitting':
        is_splitting = True
    elif tax_mode == 'single':
        is_splitting = False
    else:
        is_splitting = has_partner and situation != 'single_parent'

    church_tax_rate = float(getattr(profile, 'church_tax_rate', 0) or 0)

    # Children & independence dates
    children_profiles = list(user.children.all()) if hasattr(user, 'children') else []

    # 1. Historical Tax Assessments & Self-Calibration
    assessments_qs = TaxAssessment.objects.filter(user=user).select_related('linked_document').order_by('-year')
    assessments = list(assessments_qs)

    learned_deduction_amount = None
    learned_deduction_ratio = None
    calibration_multiplier = 1.0
    historical_avg_effective_rate = None
    historical_by_year = {}

    if assessments:
        ded_list = []
        ratio_list = []
        mult_list = []
        eff_list = []
        for a in assessments:
            historical_by_year[a.year] = a
            zve_val = float(a.taxable_income_zve or 0)
            gross_val = float(a.gross_income or 0)
            tax_val = float(a.assessed_tax_total or 0)
            ded_val = float(a.deductible_expenses or 0)
            if ded_val <= 0 and gross_val > zve_val > 0:
                ded_val = gross_val - zve_val
            if ded_val > 0:
                ded_list.append(ded_val)
                if gross_val > 0:
                    ratio_list.append(min(0.45, ded_val / gross_val))
            if zve_val > 0 and tax_val >= 0:
                eff_list.append((tax_val / zve_val) * 100.0)
                model_res = calculate_german_income_tax(
                    zve_val,
                    splitting=(a.assessment_type == 'splitting'),
                    church_tax_rate=church_tax_rate,
                    calibration_multiplier=1.0,
                )
                model_tax = float(model_res['total_tax'])
                if model_tax > 200.0 and tax_val > 0:
                    mult_list.append(max(0.70, min(1.35, tax_val / model_tax)))

        if ded_list:
            learned_deduction_amount = round(sum(ded_list) / len(ded_list), 2)
        if ratio_list:
            learned_deduction_ratio = round(sum(ratio_list) / len(ratio_list), 4)
        if mult_list:
            calibration_multiplier = round(sum(mult_list) / len(mult_list), 4)
        if eff_list:
            historical_avg_effective_rate = round(sum(eff_list) / len(eff_list), 1)

    if len(assessments) >= 2:
        calibration_status = 'high'
        calibration_label = _('Hoch (kalibriert aus %(n)s echten Steuerbescheiden)') % {'n': len(assessments)}
    elif len(assessments) == 1:
        calibration_status = 'medium'
        calibration_label = _('Aktiv (kalibriert aus Steuerbescheid %(y)s)') % {'y': assessments[0].year}
    else:
        calibration_status = 'model'
        calibration_label = _('Standard-Tarifmodell (noch kein Steuerbescheid hinterlegt)')

    # 2. Gather current household income streams
    cfs = list(CashFlowSource.objects.filter(user=user, is_income=True).select_related('category'))
    net_earned_p1_annual = 0.0
    net_earned_p2_annual = 0.0
    for cf in cfs:
        if cf.start_date and cf.start_date.year > current_year:
            continue
        if cf.end_date and cf.end_date.year < current_year:
            continue
        name_l = (cf.name or '').lower()
        cat_l = (cf.category.name if cf.category else '').lower()
        hay = f"{name_l} {cat_l} {cf.template_id or ''}"
        if any(k in hay for k in ('kindergeld', 'miete', 'kaltmiete', 'warmmiete', 'pacht', 'dividende', 'zins')):
            continue
        mult = 12.0 if cf.frequency == 'monthly' else (4.0 if cf.frequency == 'quarterly' else (1.0 if cf.frequency == 'yearly' else 0.0))
        amt_yr = float(cf.value or 0) * mult
        if cf.owner_role == 'partner':
            net_earned_p2_annual += amt_yr
        else:
            net_earned_p1_annual += amt_yr

    # Estimate gross salary if not explicitly provided on profile
    # Typical German employee social security (~20.5%) + withholding tax factor
    gross_p1 = float(profile.annual_gross_income_p1) if (profile and profile.annual_gross_income_p1) else (net_earned_p1_annual * 1.48 if net_earned_p1_annual > 0 else 0.0)
    gross_p2 = float(profile.annual_gross_income_p2) if (profile and profile.annual_gross_income_p2) else (net_earned_p2_annual * 1.42 if net_earned_p2_annual > 0 else 0.0)

    # Pensions
    pensions = list(Pension.objects.filter(user=user))
    # Capital assets for Sparerpauschbetrag / Abgeltungsteuer estimation
    assets = list(Asset.objects.filter(user=user))
    annual_capital_gains = 0.0
    for a in assets:
        if a.asset_type in {'overnight', 'depot', 'cash'}:
            rate = float(a.interest_teaser_rate if (a.interest_teaser_rate and (not a.interest_teaser_until or a.interest_teaser_until >= today)) else (a.growth_rate or 0))
            if rate > 0 and a.value:
                annual_capital_gains += float(a.value) * (rate / 100.0)

    # Real estate & loans for 30-year Anlage V projection
    re_list = list(RealEstate.objects.filter(user=user))
    loans_list = list(Loan.objects.filter(user=user))

    base_vv_result = float(portfolio_tax_vv.get('total_taxable_result_vv', 0.0)) if portfolio_tax_vv else 0.0
    base_vv_interest = float(portfolio_tax_vv.get('total_loan_interest_annual', 0.0)) if portfolio_tax_vv else 0.0
    base_vv_rent = float(portfolio_tax_vv.get('total_gross_rent_annual', 0.0)) if portfolio_tax_vv else 0.0
    base_vv_afa = float(portfolio_tax_vv.get('total_afa_annual', 0.0)) if portfolio_tax_vv else 0.0
    base_vv_other_wk = float(portfolio_tax_vv.get('total_regular_costs_annual', 0.0)) + float(portfolio_tax_vv.get('total_invoices_annual', 0.0)) if portfolio_tax_vv else 0.0

    # Ages & retirement years
    p1_birth_year = profile.birth_date.year if (profile and profile.birth_date) else (current_year - 40)
    p2_birth_year = profile.partner_birth_date.year if (profile and profile.partner_birth_date) else (current_year - 38)
    p1_ret_age = int(getattr(profile, 'retirement_age', 67) or 67)
    p2_ret_age = int(getattr(profile, 'partner_retirement_age', 67) or 67)
    p1_ret_year = p1_birth_year + p1_ret_age
    p2_ret_year = p2_birth_year + p2_ret_age

    inflation_rate = float(getattr(profile, 'inflation_rate', 2.0) or 2.0) / 100.0
    salary_growth = float(getattr(profile, 'salary_increase', 1.5) or 1.5) / 100.0
    pension_growth = float(getattr(profile, 'pension_increase', 1.0) or 1.0) / 100.0

    # 3. Run 30-Year Holistic Tax Projection
    projection_years = []
    chart_labels = []
    chart_total_tax = []
    chart_zve = []
    chart_effective_rate = []
    chart_historical_actual_tax = []
    tax_flip_year = None
    prev_vv_negative = base_vv_result < 0

    # Include up to 5 past years if historical assessments exist so the chart shows Past (Actual) -> Future (Projected)
    min_hist_year = min([a.year for a in assessments], default=current_year)
    start_year = max(current_year - 5, min(current_year, min_hist_year))
    end_year = current_year + 30

    for yr in range(start_year, end_year + 1):
        yr_offset = max(0, yr - current_year)
        p1_is_retired = yr >= p1_ret_year
        p2_is_retired = (yr >= p2_ret_year) if has_partner else True

        # Dependent children in year `yr`
        dep_children_yr = 0
        for ch in children_profiles:
            ind_date = ch.independence_date
            if ch.birth_date and ch.birth_date.year <= yr and (not ind_date or ind_date.year >= yr):
                dep_children_yr += 1

        # A. Earned Gross Income in year `yr`
        yr_gross_earned = 0.0
        if not p1_is_retired:
            yr_gross_earned += gross_p1 * ((1.0 + salary_growth) ** yr_offset)
        if has_partner and not p2_is_retired:
            yr_gross_earned += gross_p2 * ((1.0 + salary_growth) ** yr_offset)

        # B. Taxable Pension Income in year `yr`
        yr_taxable_pension = 0.0
        yr_gross_pension = 0.0
        if p1_is_retired or (has_partner and p2_is_retired):
            for p in pensions:
                owner_ret = p2_is_retired if p.owner_role == 'partner' else p1_is_retired
                owner_ret_yr = p2_ret_year if p.owner_role == 'partner' else p1_ret_year
                if not owner_ret or p.payout_type == 'lump_sum':
                    continue
                monthly_gross = float(p.gross_payout_amount or p.expected_payout or 0.0)
                if p.pension_type == 'statutory' and monthly_gross <= 0 and p.statutory_points:
                    monthly_gross = float(p.statutory_points) * float(p.point_value or Decimal('40.79'))
                annual_p = monthly_gross * 12.0 * ((1.0 + pension_growth) ** yr_offset)
                yr_gross_pension += annual_p
                if p.pension_type == 'statutory':
                    share = _drv_taxable_cohort_share(owner_ret_yr)
                    yr_taxable_pension += annual_p * share
                elif p.pension_type in {'civil_service', 'occupational_fund'}:
                    yr_taxable_pension += annual_p * 0.95
                else:
                    # Private annuity: low Ertragsanteil (§ 22 EStG, ~17% at age 67)
                    yr_taxable_pension += annual_p * 0.17

        # C. Rental Real Estate (Anlage V) in year `yr`
        # Rent & maintenance grow with inflation; AfA stays constant; loan interest declines with amortization (~4.5% decay/yr)
        yr_vv_rent = base_vv_rent * ((1.0 + inflation_rate) ** yr_offset)
        yr_vv_interest = base_vv_interest * (max(0.0, 1.0 - 0.045 * yr_offset))
        yr_vv_wk = base_vv_afa + yr_vv_interest + (base_vv_other_wk * ((1.0 + inflation_rate) ** yr_offset))
        yr_vv_taxable = yr_vv_rent - yr_vv_wk if base_vv_rent > 0 or base_vv_afa > 0 else 0.0
        if prev_vv_negative and yr_vv_taxable > 0 and tax_flip_year is None and yr >= current_year:
            tax_flip_year = yr

        # D. Deductions & Life-Phase Allowances (Vorsorgeaufwendungen, Werbungskosten, Alleinerziehende, Kinder)
        if profile and profile.typical_annual_deductions is not None:
            base_ded = float(profile.typical_annual_deductions)
        elif learned_deduction_ratio is not None and (yr_gross_earned + yr_gross_pension) > 0:
            base_ded = (yr_gross_earned + yr_gross_pension) * learned_deduction_ratio
        elif learned_deduction_amount is not None and not p1_is_retired:
            base_ded = learned_deduction_amount
        else:
            # Standard social security pension/health deductions (~18% on earned income, ~11.5% on pensions) + Arbeitnehmer-Pauschbetrag (1.230 €)
            active_workers = (0 if p1_is_retired else 1) + (1 if (has_partner and not p2_is_retired) else 0)
            base_ded = (yr_gross_earned * 0.185) + (yr_gross_pension * 0.115) + (active_workers * 1230.0)

        # Alleinerziehenden-Entlastungsbetrag (§ 24b EStG: 4.260 € + 240 € per additional child)
        single_parent_allowance = 0.0
        if (situation == 'single_parent' or not has_partner) and dep_children_yr > 0:
            single_parent_allowance = 4260.0 + max(0, dep_children_yr - 1) * 240.0

        # Compute zvE for year `yr`
        yr_zve = max(0.0, yr_gross_earned + yr_taxable_pension + yr_vv_taxable - base_ded - single_parent_allowance)

        # Günstigerprüfung Kinderfreibetrag (§ 32 Abs. 6 EStG: ~9,600 € per child vs. 3,060 € Kindergeld)
        tax_without_kfb = calculate_german_income_tax(
            yr_zve,
            splitting=is_splitting,
            church_tax_rate=church_tax_rate,
            calibration_multiplier=calibration_multiplier,
        )
        if dep_children_yr > 0:
            kfb_total = dep_children_yr * 9600.0
            kindergeld_yr = dep_children_yr * 3060.0
            tax_with_kfb = calculate_german_income_tax(
                max(0.0, yr_zve - kfb_total),
                splitting=is_splitting,
                church_tax_rate=church_tax_rate,
                calibration_multiplier=calibration_multiplier,
            )
            tax_saving_kfb = float(tax_without_kfb['income_tax']) - float(tax_with_kfb['income_tax'])
            if tax_saving_kfb > kindergeld_yr:
                # Extra tax benefit beyond Kindergeld already received
                extra_benefit = tax_saving_kfb - kindergeld_yr
                total_yr_tax = max(0.0, float(tax_without_kfb['total_tax']) - extra_benefit)
                tax_res = dict(tax_without_kfb)
                tax_res['total_tax'] = Decimal(str(round(total_yr_tax, 2)))
            else:
                tax_res = tax_without_kfb
        else:
            tax_res = tax_without_kfb

        # Capital gains tax (Abgeltungsteuer 25% + Soli vs. personal marginal rate Günstigerprüfung in retirement)
        sparer_pausch = 2000.0 if is_splitting else 1000.0
        taxable_cap = max(0.0, annual_capital_gains * ((1.0 + 0.02) ** yr_offset) - sparer_pausch)
        cap_rate = min(0.26375, (tax_res['marginal_rate'] / 100.0)) if tax_res['marginal_rate'] > 0 else 0.0
        cap_tax = taxable_cap * cap_rate

        total_tax_yr = float(tax_res['total_tax']) + cap_tax
        hist_obj = historical_by_year.get(yr)

        phase_label = (
            str(_('Ruhestand')) if (p1_is_retired and p2_is_retired)
            else (str(_('Teil-Ruhestand')) if (p1_is_retired or (has_partner and p2_is_retired))
            else (str(_('Familienphase (%s Kd.)') % dep_children_yr) if dep_children_yr > 0 else str(_('Erwerbsphase'))))
        )

        row = {
            'year': yr,
            'phase_label': phase_label,
            'dep_children': dep_children_yr,
            'gross_earned': round(yr_gross_earned, 2),
            'taxable_pension': round(yr_taxable_pension, 2),
            'vv_taxable': round(yr_vv_taxable, 2),
            'deductions': round(base_ded + single_parent_allowance, 2),
            'zve': round(yr_zve, 2),
            'estimated_tax': round(total_tax_yr, 2),
            'effective_rate': tax_res['effective_rate'],
            'marginal_rate': tax_res['marginal_rate'],
            'actual_tax': float(hist_obj.assessed_tax_total) if hist_obj else None,
            'actual_refund': float(hist_obj.refund_or_payment) if hist_obj else None,
        }
        projection_years.append(row)
        chart_labels.append(str(yr))
        chart_total_tax.append(round(total_tax_yr, 0))
        chart_zve.append(round(yr_zve, 0))
        chart_effective_rate.append(tax_res['effective_rate'])
        chart_historical_actual_tax.append(round(float(hist_obj.assessed_tax_total), 0) if hist_obj else None)

    # Current year & retirement year snapshots
    current_row = next((r for r in projection_years if r['year'] == current_year), projection_years[0])
    retirement_row = next((r for r in projection_years if r['year'] >= p1_ret_year), projection_years[-1])

    # Estimate current year refund / additional payment from Anlage V + deductions
    marginal_dec = Decimal(str(current_row['marginal_rate'] / 100.0)) if current_row['marginal_rate'] > 0 else Decimal('0.35')
    estimated_vv_refund = (-Decimal(str(current_row['vv_taxable'])) * marginal_dec).quantize(Decimal('0.01'))

    # Life-phase optimization & educational hints
    tax_hints = []
    if calibration_status == 'model':
        tax_hints.append(
            str(_("Steuerbescheid hochladen zur Kalibrierung: Lade deinen letzten Einkommensteuerbescheid als PDF hoch – das System liest zvE, Steuerlast und Abzüge ohne KI aus und kalibriert deine 30-Jahres-Prognose automatisch."))
        )
    if (situation == 'single_parent' or not has_partner) and any(r['dep_children'] > 0 for r in projection_years if r['year'] == current_year):
        tax_hints.append(
            str(_("Entlastungsbetrag für Alleinerziehende (§ 24b EStG): In deiner Prognose werden 4.260 € (+ 240 € je weiterem Kind) automatisch bis zum Selbstständigkeits-Jahr deiner Kinder steuermindernd berücksichtigt."))
        )
    if tax_flip_year:
        tax_hints.append(
            str(_(f"Immobilien Zins-Tilgungs-Wechsel ab {tax_flip_year}: Durch sinkende Darlehenszinsen und steigende Mieten dreht dein Vermietungsergebnis (Anlage V) voraussichtlich ab {tax_flip_year} ins Positive (Steuernachzahlung statt Erstattung)."))
        )
    if retirement_row and retirement_row['estimated_tax'] > 0:
        cohort_pct = round(_drv_taxable_cohort_share(p1_ret_year) * 100, 1)
        tax_hints.append(
            str(_(f"Steuerlast im Ruhestand (ab {p1_ret_year}): Bei deinem Rentenbeginn liegt der steuerpflichtige Anteil der gesetzlichen Rente bei {cohort_pct} %. Deine geschätzte Einkommensteuer im ersten Rentenjahr beträgt ca. {retirement_row['estimated_tax']:,.0f} €/Jahr (Ø {retirement_row['effective_rate']} %)."))
        )

    return {
        'is_splitting': is_splitting,
        'tax_mode': tax_mode,
        'church_tax_rate': church_tax_rate,
        'calibration_status': calibration_status,
        'calibration_label': calibration_label,
        'calibration_multiplier': calibration_multiplier,
        'learned_deduction_amount': learned_deduction_amount,
        'learned_deduction_ratio_pct': round(learned_deduction_ratio * 100.0, 1) if learned_deduction_ratio else None,
        'historical_avg_effective_rate': historical_avg_effective_rate,
        'current_year': current_year,
        'current_row': current_row,
        'retirement_year': p1_ret_year,
        'retirement_row': retirement_row,
        'estimated_vv_refund': float(estimated_vv_refund),
        'calibrated_marginal_rate': current_row['marginal_rate'] if current_row['marginal_rate'] > 0 else 35.0,
        'tax_flip_year': tax_flip_year,
        'tax_hints': tax_hints,
        'assessments': assessments,
        'projection_years': [r for r in projection_years if r['year'] >= current_year][:25],
        'chart_json': {
            'labels': chart_labels,
            'estimated_tax': chart_total_tax,
            'actual_tax': chart_historical_actual_tax,
            'zve': chart_zve,
            'effective_rate': chart_effective_rate,
        },
    }
