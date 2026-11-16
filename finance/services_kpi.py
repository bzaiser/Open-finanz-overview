from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _


SUBPAGE_KPI_IDS = {
    'emergency_runway',
    'disability_gap',
    'survivor_gap',
    'cash_reserve_status',
    'tax_annual_estimated',
    'real_estate_equity',
    'renovation_reserve_monthly',
}


def resolve_dashboard_subpage_kpis(user, visible_ids, target_date=None, forecast_point=None, baseline_point=None):
    """
    Single Source of Truth resolver for subpage KPI cards shown on the Dashboard.
    Lazily evaluates only the KPIs that are actually visible in the user's dashboard layout,
    and projects them dynamically to `target_date` (Stichtag) and stress-test `baseline_point`.
    """
    needed = set(visible_ids or ()) & SUBPAGE_KPI_IDS
    if not needed:
        return {}

    today = timezone.localdate()
    target_dt = target_date or today
    profile = getattr(user, 'profile', None)
    currency = (getattr(profile, 'currency', 'EUR') or 'EUR')

    results = {}
    risk_audit = None
    if needed & {'emergency_runway', 'disability_gap', 'survivor_gap', 'cash_reserve_status'}:
        from .services_risk import calculate_protection_audit
        risk_audit = calculate_protection_audit(user)

    # 1. Notgroschen-Reichweite (Emergency Fund Runway)
    if 'emergency_runway' in needed:
        if forecast_point:
            liq = max(0.0, float(forecast_point.get('real_asset_total', 0.0)) + max(0.0, float(forecast_point.get('real_accumulated_cash', 0.0))))
            exp = float(forecast_point.get('monthly_expenses', 0.0) or 0.0)
            months_cov = round(liq / exp, 1) if exp > 0 else round(risk_audit.get('emergency_months_covered', 0.0), 1)
        else:
            months_cov = round(risk_audit.get('emergency_months_covered', 0.0), 1)
            liq = float(risk_audit.get('emergency_reserve', 0.0) or risk_audit.get('total_liquid', 0.0))
            exp = float(risk_audit.get('monthly_expenses', 0.0) or 0.0)

        delta_val = None
        if baseline_point and forecast_point:
            b_liq = max(0.0, float(baseline_point.get('real_asset_total', 0.0)) + max(0.0, float(baseline_point.get('real_accumulated_cash', 0.0))))
            b_exp = float(baseline_point.get('monthly_expenses', 0.0) or 0.0)
            b_cov = round(b_liq / b_exp, 1) if b_exp > 0 else months_cov
            diff = round(months_cov - b_cov, 1)
            if abs(diff) >= 0.1:
                delta_val = diff

        target_m = risk_audit.get('target_months', 3)
        results['emergency_runway'] = {
            'id': 'emergency_runway',
            'value': months_cov,
            'decimals': 1,
            'unit': str(_('Mt.')),
            'subtitle': str(_(f"Ziel: {target_m} Monate")),
            'delta': delta_val,
            'delta_unit': str(_('Mt.')),
            'link_url': f"{reverse('finance:pension_plan')}?tab=risk_check",
            'hover_rows': [
                {'label': str(_('Liquides Vermögen (Stichtag)')), 'value': f"{liq:,.0f} {currency}"},
                {'label': str(_('Monatliche Ausgaben')), 'value': f"{exp:,.0f} {currency}"},
                {'label': str(_('Empfohlenes Ziel')), 'value': f"{target_m} {str(_('Monate'))}"},
            ],
        }

    # 2. BU-Versorgungslücke (Disability Gap)
    if 'disability_gap' in needed:
        ret_age = int(getattr(profile, 'retirement_age', 67) or 67)
        birth_year = profile.birth_date.year if (profile and profile.birth_date) else (today.year - 40)
        is_retired_at_target = target_dt.year >= (birth_year + ret_age)
        if is_retired_at_target:
            gap_bu = 0.0
            subtitle = str(_('Im Ruhestand nicht relevant'))
        else:
            gap_bu = round(float(risk_audit.get('disability_gap_primary', 0.0)), 0)
            subtitle = str(_('Lücke (80 %-Netto-Regel)')) if gap_bu > 0 else str(_('Bedarf vollständig gedeckt'))
        results['disability_gap'] = {
            'id': 'disability_gap',
            'value': gap_bu,
            'decimals': 0,
            'unit': f"{currency}/Mt.",
            'subtitle': subtitle,
            'delta': None,
            'delta_unit': currency,
            'link_url': f"{reverse('finance:pension_plan')}?tab=risk_check",
            'hover_rows': [
                {'label': str(_('Bedarf (80 % Netto / Ausg.)')), 'value': f"{risk_audit.get('disability_target_primary', 0):,.0f} {currency}"},
                {'label': str(_('DRV EM-Rente')), 'value': f"{risk_audit.get('drv_disability_primary', 0):,.0f} {currency}"},
                {'label': str(_('Private BU-Rente')), 'value': f"{risk_audit.get('bu_monthly_primary', 0):,.0f} {currency}"},
            ],
        }

    # 3. Hinterbliebenenschutz-Lücke (Survivor / Term Life Gap)
    if 'survivor_gap' in needed:
        covered = float(risk_audit.get('term_life_covered', 0.0))
        loan_debt_t = float(forecast_point.get('real_loan_total', 0.0)) if forecast_point else float(risk_audit.get('total_loan_debt', 0.0))
        # Recalculate recommended term life with dynamic loan debt & dependent children at target_date
        children_profiles = list(user.children.all()) if hasattr(user, 'children') else []
        dep_children_t = sum(
            1 for ch in children_profiles
            if ch.birth_date and ch.birth_date <= target_dt and (not ch.independence_date or ch.independence_date >= target_dt)
        )
        has_partner = bool(risk_audit.get('has_partner'))
        annual_inc = float(risk_audit.get('primary_earned_monthly', 0.0)) * 12.0
        mult = 5.0 if dep_children_t > 0 else (3.0 if has_partner else 0.0)
        rec_t = round(loan_debt_t + annual_inc * mult, 0) if (has_partner or dep_children_t > 0 or loan_debt_t > 10000.0) else 0.0
        gap_surv = round(max(0.0, rec_t - covered), 0)
        results['survivor_gap'] = {
            'id': 'survivor_gap',
            'value': gap_surv,
            'decimals': 0,
            'unit': currency,
            'subtitle': str(_('Todesfall-Lücke')) if gap_surv > 0 else str(_('Ausreichend abgesichert')),
            'delta': None,
            'delta_unit': currency,
            'link_url': f"{reverse('finance:pension_plan')}?tab=risk_check",
            'hover_rows': [
                {'label': str(_('Empfohlene Deckung')), 'value': f"{rec_t:,.0f} {currency}"},
                {'label': str(_('Vorhandene Risikoleben')), 'value': f"{covered:,.0f} {currency}"},
                {'label': str(_('Restschuld (Stichtag)')), 'value': f"{loan_debt_t:,.0f} {currency}"},
            ],
        }

    # 4. Physische Bargeldreserve (Cash Reserve)
    if 'cash_reserve_status' in needed:
        amt = round(float(risk_audit.get('cash_reserve_amount', 0.0)), 0)
        tgt = round(float(risk_audit.get('cash_reserve_target', 500.0)), 0)
        results['cash_reserve_status'] = {
            'id': 'cash_reserve_status',
            'value': amt,
            'decimals': 0,
            'unit': currency,
            'subtitle': f"{str(_('Richtwert:'))} {tgt:,.0f} {currency}",
            'delta': None,
            'delta_unit': currency,
            'link_url': f"{reverse('finance:pension_plan')}?tab=risk_check",
            'hover_rows': [
                {'label': str(_('Erfasster Barbestand')), 'value': f"{amt:,.0f} {currency}"},
                {'label': str(_('Haushalts-Richtwert')), 'value': f"{tgt:,.0f} {currency}"},
                {'label': str(_('Lücke')), 'value': f"{max(0.0, tgt - amt):,.0f} {currency}"},
            ],
        }

    # 5. Geschätzte Jahressteuerlast (Holistic Tax Cockpit for target_date.year)
    if 'tax_annual_estimated' in needed:
        from .services_tax import calculate_holistic_tax_cockpit
        cockpit = calculate_holistic_tax_cockpit(user)
        proj = cockpit.get('projection_years', [])
        yr_row = next((r for r in proj if r['year'] == target_dt.year), None) or (proj[-1] if proj else cockpit.get('current_row', {}))
        est_tax = round(float(yr_row.get('estimated_tax', 0.0)), 0)
        eff_rate = yr_row.get('effective_rate', 0.0)
        results['tax_annual_estimated'] = {
            'id': 'tax_annual_estimated',
            'value': est_tax,
            'decimals': 0,
            'unit': f"{currency}/J.",
            'subtitle': f"Ø {eff_rate:.1f} % · {yr_row.get('phase_label', '')}",
            'delta': None,
            'delta_unit': currency,
            'link_url': f"{reverse('finance:real_estate_loans')}?tab=tax-docs",
            'hover_rows': [
                {'label': str(_('Simulationsjahr')), 'value': str(yr_row.get('year', target_dt.year))},
                {'label': str(_('zvE (geschätzt)')), 'value': f"{yr_row.get('zve', 0):,.0f} {currency}"},
                {'label': str(_('Grenzsteuersatz')), 'value': f"{yr_row.get('marginal_rate', 0):.1f} %"},
            ],
        }

    # 6 & 7. Real Estate Equity & Renovation Reserve
    if needed & {'real_estate_equity', 'renovation_reserve_monthly'}:
        if 'real_estate_equity' in needed:
            if forecast_point:
                re_val = float(forecast_point.get('real_real_estate_total', 0.0))
                debt_val = float(forecast_point.get('real_loan_total', 0.0))
            else:
                from .services_realestate import get_real_estate_overview
                ov = get_real_estate_overview(user)
                re_val = float(ov.get('total_property_value', 0.0))
                debt_val = float(ov.get('total_loan_debt', 0.0))
            equity = round(re_val - debt_val, 0)
            ltv = round((debt_val / re_val * 100.0), 1) if re_val > 0 else 0.0

            delta_eq = None
            if baseline_point and forecast_point:
                b_eq = float(baseline_point.get('real_real_estate_total', 0.0)) - float(baseline_point.get('real_loan_total', 0.0))
                d_eq = round(equity - b_eq, 0)
                if abs(d_eq) >= 1:
                    delta_eq = d_eq

            results['real_estate_equity'] = {
                'id': 'real_estate_equity',
                'value': equity,
                'decimals': 0,
                'unit': currency,
                'subtitle': f"LTV: {ltv:.1f} %",
                'delta': delta_eq,
                'delta_unit': currency,
                'link_url': reverse('finance:real_estate_loans'),
                'hover_rows': [
                    {'label': str(_('Immobilienwert (Stichtag)')), 'value': f"{re_val:,.0f} {currency}"},
                    {'label': str(_('Restschuld (Stichtag)')), 'value': f"-{debt_val:,.0f} {currency}"},
                    {'label': str(_('Beleihungsauslauf (LTV)')), 'value': f"{ltv:.1f} %"},
                ],
            }

        if 'renovation_reserve_monthly' in needed:
            from .services_realestate import get_real_estate_overview
            ov = get_real_estate_overview(user)
            roadmap = ov.get('components_roadmap', {})
            m_res = round(float(roadmap.get('recommended_monthly_reserve', 0.0)), 0)
            tot_20 = round(float(roadmap.get('total_20yr_cost', 0.0)), 0)
            results['renovation_reserve_monthly'] = {
                'id': 'renovation_reserve_monthly',
                'value': m_res,
                'decimals': 0,
                'unit': f"{currency}/Mt.",
                'subtitle': str(_('20-J.-Sanierungsfahrplan')),
                'delta': None,
                'delta_unit': currency,
                'link_url': f"{reverse('finance:real_estate_loans')}?tab=components",
                'hover_rows': [
                    {'label': str(_('20-Jahres-Prognose')), 'value': f"{tot_20:,.0f} {currency}"},
                    {'label': str(_('Überwachte Bauteile')), 'value': str(len(roadmap.get('all_components', [])))},
                ],
            }

    return results
