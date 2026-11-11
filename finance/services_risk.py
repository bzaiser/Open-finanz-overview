from decimal import Decimal
from django.utils.translation import gettext as _
from .models import Asset, CashFlowSource, InsurancePolicy, Loan, Pension, RealEstate


NON_EARNED_TEMPLATE_IDS = {
    'inc_kindergeld',
    'inc_dividenden',
    'inc_witwenrente',
    'inc_alg1',
    'inc_buergergeld',
    'inc_wohngeld',
    'inc_kinderzuschlag',
    'inc_bafoeg',
    'inc_unterhalt',
    'inc_em_rente',
    'inc_pflegegeld',
}


def is_earned_income_cf(cf):
    """Returns True if a CashFlowSource represents active employment/self-employed income."""
    if not cf.is_income:
        return False
    if cf.template_id and cf.template_id in NON_EARNED_TEMPLATE_IDS:
        return False
    slug = (cf.category.slug.lower() if cf.category and cf.category.slug else '')
    if slug in {'familie-kinder', 'investment', 'sozialleistungen', 'bildung'}:
        return False
    name_lower = (cf.name or '').lower()
    transfer_keywords = (
        'kindergeld', 'elterngeld', 'wohngeld', 'bürgergeld', 'buergergeld',
        'alg ', 'arbeitslosengeld', 'bafö', 'bafoeg', 'unterhalt',
        'dividende', 'zins', 'witwen', 'waisen', 'rente', 'pflegegeld'
    )
    if any(kw in name_lower for kw in transfer_keywords):
        return False
    return True


def calculate_protection_audit(user):
    """
    Computes a structured risk & insurance protection audit tailored to the user's
    household situation, income structure, loans, assets, and active InsurancePolicy records.
    """
    profile = getattr(user, 'profile', None)
    situation = getattr(profile, 'household_situation', 'standard') if profile else 'standard'
    has_partner = bool(profile and (profile.partner_name or (profile.display_name and '&' in profile.display_name)))

    from django.utils import timezone
    from .models import PhysicalAsset
    from .services_realestate import calculate_loan_schedule

    today = timezone.localdate()
    cash_flows = list(CashFlowSource.objects.filter(CashFlowSource.active_on_q(ref_date=today), user=user).select_related('category'))
    assets = list(Asset.objects.filter(user=user))
    pensions = list(Pension.objects.filter(user=user))
    loans = list(Loan.objects.filter(user=user))
    real_estates = list(RealEstate.objects.filter(user=user, is_sold=False))
    physical_assets = list(PhysicalAsset.objects.filter(user=user, is_sold=False))
    insurances = list(InsurancePolicy.objects.filter(user=user, is_active=True))

    # 1. Income & Expense Baseline
    primary_earned = Decimal('0.00')
    partner_earned = Decimal('0.00')
    total_income = Decimal('0.00')
    monthly_expenses = Decimal('0.00')
    has_children = False

    for cf in cash_flows:
        amt = (cf.value or Decimal('0.00')) if cf.frequency == 'monthly' else ((cf.value or Decimal('0.00')) / Decimal('12'))
        if cf.is_income:
            total_income += amt
            if cf.template_id in {'inc_kindergeld', 'inc_kinderzuschlag', 'inc_unterhalt'} or 'kindergeld' in (cf.name or '').lower():
                has_children = True
            if is_earned_income_cf(cf):
                if cf.owner_role == 'partner':
                    partner_earned += amt
                elif cf.owner_role == 'joint':
                    primary_earned += amt / Decimal('2')
                    partner_earned += amt / Decimal('2')
                else:
                    primary_earned += amt
        else:
            monthly_expenses += amt
            if cf.template_id == 'exp_kinderbetreuung':
                has_children = True

    # Real estate rental income & ongoing costs
    for re in real_estates:
        if re.acquisition_date and re.acquisition_date > today:
            continue
        if re.sale_date and re.sale_date <= today:
            continue
        if re.rental_income_monthly and re.rental_income_monthly > 0:
            total_income += re.rental_income_monthly
        re_costs = (re.maintenance_costs_monthly or Decimal('0.00')) + (re.ancillary_costs_monthly or Decimal('0.00'))
        if re_costs > 0:
            monthly_expenses += re_costs

    # Physical asset storage costs
    for pa in physical_assets:
        if pa.acquisition_date and pa.acquisition_date > today:
            continue
        if pa.sale_date and pa.sale_date <= today:
            continue
        if pa.storage_costs_monthly and pa.storage_costs_monthly > 0:
            monthly_expenses += pa.storage_costs_monthly

    # Ongoing pension contributions
    for p in pensions:
        if p.monthly_contribution and p.monthly_contribution > 0:
            if not p.contribution_end_date or p.contribution_end_date >= today:
                monthly_expenses += p.monthly_contribution

    # Add unlinked active insurance premiums & loan installments to monthly outflow
    monthly_insurance_premiums = Decimal('0.00')
    for ins in insurances:
        if ins.start_date and ins.start_date > today:
            continue
        if ins.end_date and ins.end_date < today:
            continue
        prem = (ins.premium_amount or Decimal('0.00')) if ins.payment_frequency == 'monthly' else (
            ((ins.premium_amount or Decimal('0.00')) / Decimal('3')) if ins.payment_frequency == 'quarterly' else
            (((ins.premium_amount or Decimal('0.00')) / Decimal('6')) if ins.payment_frequency == 'semi_annual' else
             ((ins.premium_amount or Decimal('0.00')) / Decimal('12')))
        )
        monthly_insurance_premiums += prem
        if ins.include_in_cashflow and ins.linked_cash_flow_id is None:
            monthly_expenses += prem

    for loan in loans:
        if loan.start_date and loan.start_date > today:
            continue
        if loan.end_date and loan.end_date < today:
            continue
        monthly_expenses += (loan.monthly_installment or Decimal('0.00'))

    total_income = total_income.quantize(Decimal('0.01'))
    primary_earned = primary_earned.quantize(Decimal('0.01'))
    partner_earned = partner_earned.quantize(Decimal('0.01'))
    monthly_expenses = monthly_expenses.quantize(Decimal('0.01'))
    monthly_insurance_premiums = monthly_insurance_premiums.quantize(Decimal('0.01'))

    # 2. Liquid Reserves & Emergency Fund
    emergency_reserve = Decimal('0.00')
    total_liquid = Decimal('0.00')
    for a in assets:
        val = a.value or Decimal('0.00')
        if a.is_emergency_fund:
            emergency_reserve += val
        if a.asset_type in {'cash', 'overnight'}:
            total_liquid += val

    reserve_basis = emergency_reserve if emergency_reserve > 0 else total_liquid
    target_months = 6 if situation in {'low_income', 'single_parent', 'early_retiree'} else 3
    if situation == 'student':
        target_months = 2
    emergency_target = (monthly_expenses * Decimal(str(target_months))).quantize(Decimal('0.01'))
    emergency_months_covered = float((reserve_basis / monthly_expenses).quantize(Decimal('0.1'))) if monthly_expenses > 0 else 0.0

    # 3. Disability (BU / Erwerbsminderung) Gap for Primary Person
    drv_disability_primary = Decimal('0.00')
    for p in pensions:
        if p.disability_pension_net and p.owner_role in {'primary', 'joint'}:
            drv_disability_primary += p.disability_pension_net

    bu_monthly_primary = Decimal('0.00')
    for ins in insurances:
        if ins.insurance_type == 'disability' and ins.insured_person in {'primary', 'joint'} and ins.coverage_monthly_payout:
            bu_monthly_primary += ins.coverage_monthly_payout

    # Target protection: 80% of net earned income (or at least essential expenses if not employed)
    disability_target_primary = (primary_earned * Decimal('0.80')).quantize(Decimal('0.01')) if primary_earned > 0 else Decimal('0.00')
    disability_covered_primary = drv_disability_primary + bu_monthly_primary
    disability_gap_primary = max(Decimal('0.00'), disability_target_primary - disability_covered_primary)

    # 4. Survivor / Partner Death Gap
    term_life_partner = Decimal('0.00')
    term_life_primary = Decimal('0.00')
    for ins in insurances:
        if ins.insurance_type == 'term_life' and ins.coverage_lump_sum:
            if ins.insured_person in {'partner', 'joint'}:
                term_life_partner += ins.coverage_lump_sum
            if ins.insured_person in {'primary', 'joint'}:
                term_life_primary += ins.coverage_lump_sum

    total_loan_debt = sum(
        (calculate_loan_schedule(l).get('current_balance') or Decimal('0.00'))
        for l in loans
    )
    # Recommended lump sum: remaining debt + 3 years of partner/primary income replacement
    annual_income_ref = max(primary_earned, partner_earned) * Decimal('12')
    recommended_term_life = total_loan_debt + (annual_income_ref * Decimal('3') if (has_partner or has_children) else Decimal('0.00'))
    term_life_covered = max(term_life_partner, term_life_primary)
    term_life_gap = max(Decimal('0.00'), recommended_term_life - term_life_covered) if (has_partner or has_children or total_loan_debt > 0) else Decimal('0.00')

    # 5. Job Loss Runway (ALG I = 60% / 67% of primary earned net)
    alg1_rate = Decimal('0.67') if has_children else Decimal('0.60')
    alg1_estimated = (primary_earned * alg1_rate).quantize(Decimal('0.01'))
    income_without_primary = (total_income - primary_earned) + alg1_estimated
    job_loss_monthly_deficit = max(Decimal('0.00'), monthly_expenses - income_without_primary)
    if primary_earned <= 0:
        job_loss_runway_months = None
    elif job_loss_monthly_deficit == 0:
        job_loss_runway_months = 999  # Fully covered by ALG I + remaining income
    else:
        job_loss_runway_months = float((total_liquid / job_loss_monthly_deficit).quantize(Decimal('0.1')))

    # 6. Prioritized Insurance Checklist by Target Group
    existing_types = {ins.insurance_type for ins in insurances}
    # Also check CashFlowSource template_ids in case user entered insurances only as CashFlows
    cf_tpls = {cf.template_id for cf in cash_flows if cf.template_id}
    tpl_to_type = {
        'exp_haftpflicht': 'liability',
        'exp_bu': 'disability',
        'exp_risikoleben': 'term_life',
        'exp_krankentagegeld': 'sick_pay',
        'exp_hausrat': 'household',
        'exp_wohngebaeude': 'building',
        'exp_rechtsschutz': 'legal',
        'exp_kfz_versicherung': 'kfz',
        'exp_unfall': 'accident',
    }
    for tpl_id, ins_type in tpl_to_type.items():
        if tpl_id in cf_tpls:
            existing_types.add(ins_type)

    checklist = []

    def add_check(ins_type, title, priority, needed, reason, covered_hint=""):
        is_covered = ins_type in existing_types
        if not needed and not is_covered:
            return
        status = 'covered' if is_covered else ('critical' if priority == 'essential' else 'recommended')
        checklist.append({
            'type': ins_type,
            'title': str(title),
            'priority': priority,
            'status': status,
            'reason': str(reason),
            'covered_hint': str(covered_hint),
        })

    add_check(
        'liability',
        _('Privathaftpflichtversicherung'),
        'essential',
        True,
        _('Unverzichtbarer Existenzschutz für jede Lebenslage (oft unter 6 €/Monat).'),
        _('Policen-Schutz aktiv') if 'liability' in existing_types else _('Fehlt – höchste Priorität!'),
    )

    need_bu = situation in {'standard', 'low_income', 'single_parent'} and primary_earned > 0
    add_check(
        'disability',
        _('Berufsunfähigkeits- / Erwerbsunfähigkeitsschutz'),
        'essential' if (situation == 'single_parent' or primary_earned > 0) else 'optional',
        need_bu,
        _('Schließt die Lücke zwischen Nettoeinkommen und gesetzlicher Erwerbsminderungsrente.'),
        f"{_('Lücke')}: {disability_gap_primary:,.0f} €/mtl." if disability_gap_primary > 0 else _('Bedarf gedeckt'),
    )

    need_term_life = has_partner or has_children or total_loan_debt > Decimal('10000')
    add_check(
        'term_life',
        _('Risikolebensversicherung'),
        'essential' if (has_children or total_loan_debt > Decimal('30000')) else 'recommended',
        need_term_life,
        _('Sichert Hinterbliebene & laufende Kredite bei Tod eines Partners / Elternteils ab.'),
        f"{_('Empfehlung')}: ca. {recommended_term_life:,.0f} €" if term_life_gap > 0 else _('Abgesichert'),
    )

    if primary_earned > Decimal('1200') and situation not in {'student', 'unemployed', 'early_retiree'}:
        add_check(
            'sick_pay',
            _('Krankentagegeldversicherung'),
            'recommended',
            True,
            _('Überbrückt ab Woche 7 die Differenz zwischen Krankengeld (~70 % Netto) und Gehalt.'),
        )

    if real_estates:
        add_check(
            'building',
            _('Wohngebäudeversicherung'),
            'essential',
            True,
            _('Pflichtschutz bei Immobilienbesitz gegen Feuer-, Sturm- und Leitungswasserschäden.'),
        )

    add_check(
        'household',
        _('Hausratversicherung'),
        'optional' if situation in {'student', 'unemployed'} else 'recommended',
        situation not in {'student'} or 'household' in existing_types,
        _('Sinnvoll, wenn der Wiederbeschaffungswert des Hausrats die eigenen Rücklagen übersteigt.'),
    )

    # Optimization / Savings Hints for low-income / unemployed / student
    optimization_hints = []
    if situation in {'low_income', 'unemployed', 'student', 'single_parent'}:
        if 'accident' in existing_types and 'disability' not in existing_types:
            optimization_hints.append(str(_('Unfallversicherung prüft nur Unfallfolgen, keine Krankheiten – BU/Grundfähigkeit hat Vorrang.')))
        if emergency_months_covered < 1.0:
            optimization_hints.append(str(_('Notgroschen deckt unter 1 Monat Fixkosten: Kleiner monatlicher Puffer (z. B. 25–50 €) verhindert teure Dispozinsen.')))
        if situation == 'unemployed':
            optimization_hints.append(str(_('Bei Bürgergeld-Bezug: Angemessene Pflicht-/Privathaftpflicht & KFZ-Haftpflicht können einkommensmindernd berücksichtigt werden.')))

    return {
        'situation': situation,
        'has_partner': has_partner,
        'has_children': has_children,
        'primary_earned_monthly': float(primary_earned),
        'partner_earned_monthly': float(partner_earned),
        'total_income_monthly': float(total_income),
        'monthly_expenses': float(monthly_expenses),
        'monthly_insurance_premiums': float(monthly_insurance_premiums),
        'emergency_reserve': float(reserve_basis),
        'total_liquid': float(total_liquid),
        'emergency_target': float(emergency_target),
        'emergency_target_months': target_months,
        'emergency_months_covered': emergency_months_covered,
        'drv_disability_primary': float(drv_disability_primary),
        'bu_monthly_primary': float(bu_monthly_primary),
        'disability_target_primary': float(disability_target_primary),
        'disability_covered_primary': float(disability_covered_primary),
        'disability_gap_primary': float(disability_gap_primary),
        'recommended_term_life': float(recommended_term_life),
        'term_life_covered': float(term_life_covered),
        'term_life_gap': float(term_life_gap),
        'alg1_estimated': float(alg1_estimated),
        'job_loss_monthly_deficit': float(job_loss_monthly_deficit),
        'job_loss_runway_months': job_loss_runway_months,
        'checklist': checklist,
        'optimization_hints': optimization_hints,
    }
