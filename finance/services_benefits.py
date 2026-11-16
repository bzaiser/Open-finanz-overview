from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext as _


def estimate_elterngeld_monthly(prior_net_monthly, variant='basis', has_sibling_bonus=False, config=None):
    """
    Estimates German Elterngeld (BEEG) monthly payout:
    - Basiselterngeld: 65%..67% (up to 100% below 1,000 €), clamped between min (300 €) and max (1,800 €).
    - ElterngeldPlus: 50% of Basiselterngeld (clamped between 150 € and 900 €).
    - Sibling bonus (Geschwisterbonus): +10%, at least +75 € (Basis) or +37.50 € (Plus).
    """
    if config is None:
        from .models import TaxAndBenefitConfig
        config = TaxAndBenefitConfig.get_active()

    min_basis = float(getattr(config, 'elterngeld_min_monthly', 300.0) or 300.0)
    max_basis = float(getattr(config, 'elterngeld_max_monthly', 1800.0) or 1800.0)

    net = max(0.0, float(prior_net_monthly or 0.0))
    if net <= 0.0:
        base = min_basis
    else:
        if net < 1000.0:
            rate = min(1.00, 0.67 + ((1000.0 - net) / 2.0) * 0.001)
        elif net < 1200.0:
            rate = 0.67
        elif net < 1240.0:
            rate = 0.67 - ((net - 1200.0) / 2.0) * 0.001
        else:
            rate = 0.65
        base = max(min_basis, min(max_basis, net * rate))

    if variant == 'plus':
        amount = base * 0.5
        if has_sibling_bonus:
            amount += max(37.5, amount * 0.10)
    else:
        amount = base
        if has_sibling_bonus:
            amount += max(75.0, amount * 0.10)

    return round(amount, 2)


def calculate_elterngeld_and_benefits(user, tax_cockpit=None):
    """
    Checks Elterngeld eligibility (configurable zvE limit, default 175,000 €)
    and evaluates potential German statutory family/social benefits based on
    household situation, children, income, and rent expenses.
    """
    from .models import CashFlowSource, TaxAndBenefitConfig, TaxAssessment

    cfg = TaxAndBenefitConfig.get_active()
    zve_limit = float(cfg.elterngeld_zve_limit or 175000.0)
    child_benefit_m = float(cfg.child_benefit_monthly or 255.0)
    kiz_max_m = float(cfg.kiz_max_monthly or 297.0)
    buergergeld_single_m = float(cfg.buergergeld_single_monthly or 563.0)

    profile = getattr(user, 'profile', None)
    situation = getattr(profile, 'household_situation', 'standard') if profile else 'standard'
    has_partner = bool(profile and (profile.partner_name or (profile.display_name and '&' in profile.display_name)))
    today = timezone.localdate()

    # Determine relevant zvE (prefer latest TaxAssessment, fallback to tax_cockpit)
    latest_assessment = TaxAssessment.objects.filter(user=user).order_by('-year').first()
    if latest_assessment and latest_assessment.taxable_income_zve is not None:
        zve_ref = float(latest_assessment.taxable_income_zve)
        zve_source = str(_(f"Steuerbescheid {latest_assessment.year}"))
    elif tax_cockpit and tax_cockpit.get('current_row'):
        zve_ref = float(tax_cockpit['current_row'].get('zve', 0.0) or 0.0)
        zve_source = str(_("Steuer-Cockpit Schätzung"))
    else:
        from .services_tax import calculate_holistic_tax_cockpit
        tc = calculate_holistic_tax_cockpit(user)
        zve_ref = float(tc['current_row'].get('zve', 0.0) or 0.0)
        zve_source = str(_("Steuer-Cockpit Schätzung"))

    elterngeld_eligible = zve_ref <= zve_limit

    # Monthly net earned income & rent expenses
    cfs = list(CashFlowSource.objects.filter(user=user))
    net_primary_m = 0.0
    net_partner_m = 0.0
    monthly_rent_exp = 0.0
    existing_benefits = set()
    for cf in cfs:
        if cf.end_date and cf.end_date < today:
            continue
        mult = 1.0 if cf.frequency == 'monthly' else (1.0 / 3.0 if cf.frequency == 'quarterly' else (1.0 / 12.0 if cf.frequency == 'yearly' else 0.0))
        val_m = float(cf.value or 0) * mult
        tid = (cf.template_id or '').lower()
        name_l = (cf.name or '').lower()
        if cf.is_income:
            if tid in {'inc_kindergeld', 'inc_elterngeld', 'inc_kinderzuschlag', 'inc_wohngeld', 'inc_buergergeld', 'inc_bafoeg', 'inc_unterhalt'}:
                existing_benefits.add(tid)
                continue
            if any(k in name_l for k in ('kindergeld', 'elterngeld', 'wohngeld', 'kinderzuschlag', 'bürgergeld', 'miete')):
                continue
            if cf.owner_role == 'partner':
                net_partner_m += val_m
            else:
                net_primary_m += val_m
        else:
            if tid in {'exp_miete', 'exp_wohnung_miete'} or 'kaltmiete' in name_l or 'miete' in name_l:
                monthly_rent_exp += val_m

    children_profiles = list(user.children.all()) if hasattr(user, 'children') else []
    dep_children = [
        ch for ch in children_profiles
        if not ch.independence_date or ch.independence_date >= today
    ]
    # Sibling bonus applies if at least 1 child < 3 yrs or >= 2 children < 6 yrs
    young_children = [
        ch for ch in dep_children
        if ch.birth_date and ((today - ch.birth_date).days / 365.25) < 6.0
    ]
    has_sibling_bonus = len(young_children) >= 1

    est_basis_p1 = estimate_elterngeld_monthly(net_primary_m, 'basis', has_sibling_bonus=has_sibling_bonus, config=cfg) if elterngeld_eligible else 0.0
    est_plus_p1 = estimate_elterngeld_monthly(net_primary_m, 'plus', has_sibling_bonus=has_sibling_bonus, config=cfg) if elterngeld_eligible else 0.0

    # Evaluate other statutory benefits (orientational hints)
    total_household_net_m = net_primary_m + net_partner_m
    benefits_list = []

    # 1. Kindergeld
    if dep_children:
        kg_total = len(dep_children) * child_benefit_m
        benefits_list.append({
            'id': 'kindergeld',
            'title': str(_('Kindergeld')),
            'status': 'active' if 'inc_kindergeld' in existing_benefits else 'eligible',
            'badge': str(_('Aktiv / Anspruch')),
            'amount_hint': f"{kg_total:,.0f} €/Mt. ({len(dep_children)} × {child_benefit_m:.0f} €)",
            'reason': str(_("Für jedes unterhaltsberechtigte Kind im Haushalt.")),
        })

    # 2. Elterngeld
    benefits_list.append({
        'id': 'elterngeld',
        'title': str(_('Elterngeld / ElterngeldPlus')),
        'status': 'active' if 'inc_elterngeld' in existing_benefits else ('eligible' if elterngeld_eligible else 'excluded'),
        'badge': (
            str(_('Im Plan aktiv')) if 'inc_elterngeld' in existing_benefits
            else (str(_('Anspruch möglich')) if elterngeld_eligible else str(_('zvE-Grenze überschritten')))
        ),
        'amount_hint': (
            f"{est_basis_p1:,.0f} €/Mt. Basis (Plus: {est_plus_p1:,.0f} €)"
            if elterngeld_eligible else
            str(_(f"0 € (zvE {zve_ref:,.0f} € > Grenze {zve_limit:,.0f} €)"))
        ),
        'reason': str(_(f"Prüfung anhand zvE ({zve_source}) gegen gesetzliche Grenze von {zve_limit:,.0f} €.")),
    })

    # 3. Kinderzuschlag (KiZ)
    kiz_min_income = 900.0 if has_partner else 600.0
    kiz_possible = len(dep_children) > 0 and kiz_min_income <= total_household_net_m <= (3200.0 + len(dep_children) * 600.0)
    if dep_children:
        benefits_list.append({
            'id': 'kinderzuschlag',
            'title': str(_('Kinderzuschlag (KiZ)')),
            'status': 'active' if 'inc_kinderzuschlag' in existing_benefits else ('eligible' if kiz_possible else 'info'),
            'badge': str(_('Prüfen lohnt sich')) if kiz_possible else str(_('Einkommen vermutlich zu hoch/niedrig')),
            'amount_hint': str(_(f"bis zu {kiz_max_m * len(dep_children):,.0f} €/Mt. (max. {kiz_max_m:.0f} €/Kind)")),
            'reason': str(_("Für Familien mit kleinem/mittlerem Einkommen zusätzlich zum Kindergeld.")),
        })

    # 4. Wohngeld (Plus)
    wohngeld_possible = monthly_rent_exp > 0 and total_household_net_m <= (2400.0 + len(dep_children) * 550.0 + (700.0 if has_partner else 0.0))
    if monthly_rent_exp > 0 or situation in {'low_income', 'single_parent', 'student'}:
        benefits_list.append({
            'id': 'wohngeld',
            'title': str(_('Wohngeld (Mietzuschuss / Lastenzuschuss)')),
            'status': 'active' if 'inc_wohngeld' in existing_benefits else ('eligible' if wohngeld_possible else 'info'),
            'badge': str(_('Prüfen lohnt sich')) if wohngeld_possible else str(_('Abhängig von Mietstufe')),
            'amount_hint': str(_("Individuell je Mietstufe & Haushaltsgröße")),
            'reason': str(_("Zuschuss zu den Wohnkosten bei niedrigem bis mittlerem Gesamteinkommen.")),
        })

    # 5. Unterhaltsvorschuss (Single Parent)
    if situation == 'single_parent' or (not has_partner and len(dep_children) > 0):
        benefits_list.append({
            'id': 'unterhaltsvorschuss',
            'title': str(_('Unterhaltsvorschuss')),
            'status': 'active' if 'inc_unterhalt' in existing_benefits else 'eligible',
            'badge': str(_('Relevant für Alleinerziehende')),
            'amount_hint': str(_("227 € (0–5 J.) / 299 € (6–11 J.) / 394 € (12–17 J.)")),
            'reason': str(_("Falls der andere Elternteil keinen oder zu wenig Unterhalt zahlt.")),
        })

    # 6. BAföG / Bürgergeld
    if situation == 'student':
        benefits_list.append({
            'id': 'bafoeg',
            'title': str(_('BAföG / Bildungskredit')),
            'status': 'active' if 'inc_bafoeg' in existing_benefits else 'eligible',
            'badge': str(_('Für Studierende / Azubis')),
            'amount_hint': str(_("bis zu ~992 €/Mt. (inkl. Wohnzuschlag)")),
            'reason': str(_("Staatliche Ausbildungsförderung (50 % Zuschuss, 50 % zinsfreies Darlehen).")),
        })
    elif situation == 'unemployed':
        benefits_list.append({
            'id': 'buergergeld',
            'title': str(_('Bürgergeld (Grundsicherung)')),
            'status': 'active' if 'inc_buergergeld' in existing_benefits else 'eligible',
            'badge': str(_('Bei Bedarf nach ALG I')),
            'amount_hint': str(_(f"Regelsatz {buergergeld_single_m:.0f} € (Single) + angemessene Warmmiete")),
            'reason': str(_("Sichert Lebensunterhalt und Unterkunft, sofern kein ausreichendes Einkommen/Vermögen vorliegt.")),
        })

    return {
        'config': cfg,
        'effective_year': cfg.effective_year,
        'zve_ref': round(zve_ref, 2),
        'zve_source': zve_source,
        'zve_limit': zve_limit,
        'elterngeld_eligible': elterngeld_eligible,
        'net_primary_m': round(net_primary_m, 2),
        'net_partner_m': round(net_partner_m, 2),
        'has_sibling_bonus': has_sibling_bonus,
        'est_basis_p1': est_basis_p1,
        'est_plus_p1': est_plus_p1,
        'min_basis': float(cfg.elterngeld_min_monthly or 300.0),
        'max_basis': float(cfg.elterngeld_max_monthly or 1800.0),
        'benefits_list': benefits_list,
    }
