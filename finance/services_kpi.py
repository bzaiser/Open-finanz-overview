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


def build_svg_sparkline(values, width=200, height=42):
    """
    Generates normalized SVG path strings ('line' and 'area') from a sequence of numeric values.
    Downsamples to at most 10 evenly spaced points for crisp rendering.
    """
    pts = [float(v or 0.0) for v in (values or ()) if v is not None]
    if len(pts) < 2:
        return None
    if len(pts) > 10:
        step = (len(pts) - 1) / 9.0
        pts = [pts[round(i * step)] for i in range(10)]
    mn = min(pts)
    mx = max(pts)
    span = mx - mn
    pad_top = 6.0
    pad_bot = 5.0
    usable_h = height - pad_top - pad_bot
    coords = []
    for idx, val in enumerate(pts):
        x = round(idx * (width / float(len(pts) - 1)), 1)
        if span <= 1e-6:
            y = round(height - pad_bot - usable_h * 0.45, 1)
        else:
            norm = (val - mn) / span
            y = round(height - pad_bot - norm * usable_h, 1)
        coords.append((x, y))
    line_d = "M" + " L".join(f"{x},{y}" for x, y in coords)
    area_d = f"{line_d} L{width},{height} L0,{height} Z"
    return {"line": line_d, "area": area_d}


def build_segmented_progress(current_val, target_val, marker_pct=None, label=""):
    """
    Builds a 10-segment progress bar dict with optional target marker percentage.
    """
    cur = max(0.0, float(current_val or 0.0))
    tgt = float(target_val or 0.0)
    if tgt <= 0:
        return None
    raw_pct = min(100.0, max(0.0, (cur / tgt) * 100.0))
    active_count = min(10, max(0, round(raw_pct / 10.0)))
    return {
        "pct": round(raw_pct),
        "active_count": active_count,
        "segments": [i < active_count for i in range(10)],
        "marker_pct": marker_pct,
        "label": label,
    }


def get_kpi_target_url(kpi_id):
    """
    Maps any dashboard or module KPI card ID to its canonical target URL / tab.
    """
    mapping = {
        'monthly_income': f"{reverse('finance:cash_flow_list')}?type=INCOME",
        'monthly_expenses': f"{reverse('finance:cash_flow_list')}?type=EXPENSE",
        'monthly_surplus': reverse('finance:cash_flow_list'),
        'current_assets': f"{reverse('finance:assets_overview')}?tab=accounts",
        'total_physical_assets': f"{reverse('finance:assets_overview')}?tab=physical",
        'total_combined_assets': reverse('finance:assets_overview'),
        'total_pensions': f"{reverse('finance:pension_plan')}?tab=pensions",
        'expected_payout': f"{reverse('finance:pension_plan')}?tab=pensions",
        'current_pension_payout': f"{reverse('finance:pension_plan')}?tab=pensions",
        'total_real_estate': reverse('finance:real_estate_loans'),
        'total_debts': f"{reverse('finance:real_estate_loans')}#loans-section",
        'emergency_runway': f"{reverse('finance:pension_plan')}?tab=risk_check",
        'disability_gap': f"{reverse('finance:pension_plan')}?tab=risk_check",
        'survivor_gap': f"{reverse('finance:pension_plan')}?tab=risk_check",
        'cash_reserve_status': f"{reverse('finance:pension_plan')}?tab=risk_check",
        'tax_annual_estimated': f"{reverse('finance:real_estate_loans')}?tab=tax-docs",
        'real_estate_equity': reverse('finance:real_estate_loans'),
        'renovation_reserve_monthly': f"{reverse('finance:real_estate_loans')}?tab=components",
    }
    return mapping.get(kpi_id, reverse('finance:dashboard'))


def enrich_dashboard_kpi_items(summary_layout, user, profile, forecast_data, summary_widgets, current_metrics):
    """
    Attaches target_url, icon, size ('sm'|'md'|'lg'), sparkline, and progress bar data
    to every item in summary_layout.
    """
    samples = []
    if forecast_data:
        n = len(forecast_data)
        if n <= 10:
            samples = list(forecast_data)
        else:
            step = (n - 1) / 9.0
            samples = [forecast_data[round(i * step)] for i in range(10)]

    inc_series = [p.get('monthly_income', 0.0) for p in samples]
    exp_series = [p.get('monthly_expenses', 0.0) for p in samples]
    pen_series = [p.get('real_pension_total', 0.0) for p in samples]
    ast_series = [
        float(p.get('real_asset_total', 0.0)) + float(p.get('real_pension_total', 0.0)) + min(0.0, float(p.get('real_accumulated_cash', 0.0)))
        for p in samples
    ]
    phys_series = [p.get('real_physical_asset_total', 0.0) for p in samples]
    re_series = [p.get('real_real_estate_total', 0.0) for p in samples]
    debt_series = [p.get('real_loan_total', 0.0) for p in samples]
    comb_series = [a + ph + r - d for a, ph, r, d in zip(ast_series, phys_series, re_series, debt_series)]

    spark_map = {
        'monthly_income': build_svg_sparkline(inc_series),
        'monthly_expenses': build_svg_sparkline(exp_series),
        'current_assets': build_svg_sparkline(ast_series),
        'total_pensions': build_svg_sparkline(pen_series),
        'total_physical_assets': build_svg_sparkline(phys_series),
        'total_real_estate': build_svg_sparkline(re_series),
        'total_debts': build_svg_sparkline(debt_series),
        'total_combined_assets': build_svg_sparkline(comb_series),
    }

    inc_now = float(current_metrics.get('monthly_income', 0.0) or 0.0)
    exp_now = float(current_metrics.get('monthly_expenses', 0.0) or 0.0)
    exp_pen = float(current_metrics.get('expected_payout', 0.0) or 0.0)
    cur_pen = float(current_metrics.get('current_pension_payout', 0.0) or 0.0)
    target_pen = float(getattr(profile, 'target_pension_payout', 0.0) or 0.0) or (inc_now * 0.8 if inc_now > 0 else 2500.0)

    prog_map = {}
    if target_pen > 0:
        prog_map['expected_payout'] = build_segmented_progress(
            exp_pen, target_pen, marker_pct=80,
            label=f"{round(min(100.0, (exp_pen / target_pen) * 100.0))}% {_('vom Rentenziel')} ({target_pen:,.0f} {getattr(profile, 'currency', 'EUR')})"
        )
        if cur_pen > 0:
            prog_map['current_pension_payout'] = build_segmented_progress(
                cur_pen, target_pen, marker_pct=80,
                label=f"{round(min(100.0, (cur_pen / target_pen) * 100.0))}% {_('vom Rentenziel')}"
            )
    if inc_now > 0:
        savings_rate = max(0.0, (inc_now - exp_now) / inc_now * 100.0)
        prog_map['monthly_expenses'] = build_segmented_progress(
            savings_rate, 50.0, marker_pct=40,
            label=f"{_('Sparquote')}: {round(savings_rate)} %"
        )

    for item in summary_layout:
        wid = item.get('id')
        w_info = summary_widgets.get(wid, {})
        sz = item.get('size', 'sm')
        if sz not in ('sm', 'md', 'lg'):
            sz = 'sm'
        item['size'] = sz
        item['icon'] = w_info.get('icon', 'bi-graph-up')
        sub_kpi = item.get('subpage_kpi')
        item['target_url'] = sub_kpi.get('link_url') if (sub_kpi and sub_kpi.get('link_url')) else get_kpi_target_url(wid)
        item['sparkline'] = (sub_kpi.get('sparkline') if sub_kpi else None) or spark_map.get(wid)
        item['progress'] = (sub_kpi.get('progress') if sub_kpi else None) or prog_map.get(wid)



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
            'progress': build_segmented_progress(months_cov, max(6.0, float(target_m) * 1.5), marker_pct=round(float(target_m) / max(6.0, float(target_m) * 1.5) * 100), label=f"{str(_('Ziel'))}: {target_m} {str(_('Monate'))}"),
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
