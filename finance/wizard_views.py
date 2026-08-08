import json
from decimal import Decimal
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from core.models import UserProfile
from .models import (
    Category, CashFlowSource, Asset, RealEstate, Loan, Pension, AssetSnapshot
)


def _get_category_by_slug_or_name(slug, name_fallback, color_fallback="#6c757d"):
    cat = Category.objects.filter(slug=slug).first()
    if not cat:
        cat = Category.objects.filter(name__iexact=name_fallback).first()
    if not cat:
        cat = Category.objects.create(name=name_fallback, slug=slug, color=color_fallback)
    return cat


@login_required
def wizard_page_view(request):
    """
    Renders the interactive setup & document update wizard page.
    """
    profile = getattr(request.user, 'profile', None)
    categories = Category.objects.all().order_by('name')
    
    # Pre-populate existing user data so existing data isn't lost
    profile_data = {
        'display_name': profile.display_name if profile else '',
        'birth_date': profile.birth_date.strftime('%Y-%m-%d') if (profile and profile.birth_date) else '',
        'retirement_age': profile.retirement_age if profile else 67,
        'partner_name': profile.partner_name if profile else '',
        'partner_birth_date': profile.partner_birth_date.strftime('%Y-%m-%d') if (profile and profile.partner_birth_date) else '',
        'partner_retirement_age': profile.partner_retirement_age if profile else 67,
        'target_monthly_payout': float(profile.target_pension_payout) if (profile and profile.target_pension_payout) else '',
        'hide_wizard_on_start': profile.hide_wizard_on_start if profile else False,
    }

    # Pre-populate existing pensions
    pensions = Pension.objects.filter(user=request.user)
    pensions_stat = []
    pensions_priv = []
    from django.contrib.contenttypes.models import ContentType
    ct_pension = ContentType.objects.get_for_model(Pension)

    for p in pensions:
        latest_snap_date = AssetSnapshot.objects.filter(
            user=request.user, content_type=ct_pension, object_id=p.id
        ).order_by('-date').values_list('date', flat=True).first()
        
        stmt_date_str = latest_snap_date.strftime('%Y-%m-%d') if latest_snap_date else date.today().strftime('%Y-%m-%d')

        stand_today = None
        if p.pension_type == 'statutory' and p.pension_points is not None and p.point_value is not None:
            stand_today = float(p.pension_points * p.point_value)
        elif p.expected_payout_at_retirement is not None:
            stand_today = float(p.expected_payout_at_retirement)

        p_dict = {
            'existing_pension_id': p.id,
            'provider': p.provider,
            'pension_type': p.pension_type,
            'pension_points': float(p.pension_points) if p.pension_points is not None else '',
            'point_value': float(p.point_value) if p.point_value is not None else 39.32,
            'erwerbsminderung_net': float(p.disability_pension_net) if p.disability_pension_net is not None else '',
            'stand_today_net': stand_today if stand_today is not None else '',
            'expected_monthly_payout': float(p.expected_payout_at_retirement) if p.expected_payout_at_retirement is not None else '',
            'forecast_net': float(p.expected_payout_at_retirement) if p.expected_payout_at_retirement is not None else '',
            'current_capital': float(p.current_value) if p.current_value is not None else '',
            'growth_rate': float(p.growth_rate) if p.growth_rate is not None else '',
            'monthly_contribution': float(p.monthly_contribution) if p.monthly_contribution is not None else '',
            'statement_date': stmt_date_str,
            'retirement_date': p.start_payout_date.strftime('%Y-%m-%d') if p.start_payout_date else '',
        }
        if p.pension_type == 'statutory':
            pensions_stat.append(p_dict)
        else:
            pensions_priv.append(p_dict)

    # Pre-populate cash flows
    cash_flows = CashFlowSource.objects.filter(user=request.user)
    incomes = [{'name': c.name, 'amount': float(c.value), 'frequency': c.frequency} for c in cash_flows if c.is_income]
    expenses = [{'name': c.name, 'amount': float(c.value), 'frequency': c.frequency} for c in cash_flows if not c.is_income]

    # Pre-populate assets, real estate & loans
    assets = [{'name': a.name, 'value': float(a.value), 'growth_rate': float(a.growth_rate)} for a in Asset.objects.filter(user=request.user)]
    real_estates = [{'name': re.name, 'property_value': float(re.property_value), 'appreciation_rate': float(re.appreciation_rate)} for re in RealEstate.objects.filter(user=request.user)]
    loans = [{'name': l.name, 'nominal_amount': float(l.nominal_amount), 'monthly_installment': float(l.monthly_installment), 'interest_rate': float(l.interest_rate)} for l in Loan.objects.filter(user=request.user)]

    wizard_initial_json = {
        'profile': profile_data,
        'drv_statements': pensions_stat,
        'private_statements': pensions_priv,
        'incomes': incomes,
        'expenses': expenses,
        'assets': assets,
        'real_estates': real_estates,
        'loans': loans,
    }

    context = {
        'profile': profile,
        'categories': categories,
        'wizard_initial_json': json.dumps(wizard_initial_json),
    }
    return render(request, 'finance/setup_wizard.html', context)


from django.db import transaction

@login_required
def wizard_save_api(request):
    """
    API endpoint that accepts the JSON payload from the wizard and creates/updates all financial objects.
    All operations are wrapped in an atomic transaction to ensure zero partial data corruption.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    def _to_decimal(val):
        if val is None or val == '' or str(val).strip() == '':
            return None
        try:
            return Decimal(str(val).replace(',', '.').strip())
        except Exception:
            return None

    def _parse_date(val_str):
        if not val_str or not isinstance(val_str, str):
            return None
        try:
            return datetime.strptime(val_str.strip(), '%Y-%m-%d').date()
        except Exception:
            return None

    try:
        data = json.loads(request.body.decode('utf-8'))
        user = request.user

        with transaction.atomic():
            profile, _ = UserProfile.objects.get_or_create(user=user)

            # 1. Profile & Persons
            household_type = data.get('household_type', 'single')
            p1_name = str(data.get('p1_name', '') or '').strip() or user.first_name or "Person 1"
            p1_birth = _parse_date(data.get('p1_birth_date'))
            p1_ret_age = data.get('p1_retirement_age')
            
            p2_name = str(data.get('p2_name', '') or '').strip()
            p2_birth = _parse_date(data.get('p2_birth_date'))
            p2_ret_age = data.get('p2_retirement_age')

            if p1_birth:
                profile.birth_date = p1_birth
            if p1_ret_age:
                try:
                    profile.retirement_age = int(p1_ret_age)
                except (ValueError, TypeError):
                    pass

            if household_type == 'couple':
                profile.partner_name = p2_name or "Partner"
                if p2_birth:
                    profile.partner_birth_date = p2_birth
                if p2_ret_age:
                    try:
                        profile.partner_retirement_age = int(p2_ret_age)
                    except (ValueError, TypeError):
                        pass
            
            target_pension = _to_decimal(data.get('target_monthly_payout'))
            if target_pension is not None:
                profile.target_pension_payout = target_pension
                
            if 'hide_wizard_on_start' in data:
                profile.hide_wizard_on_start = bool(data.get('hide_wizard_on_start'))

            profile.display_name = p1_name if household_type == 'single' else f"{p1_name} & {p2_name or 'Partner'}"
            profile.save()

            ct_pension = ContentType.objects.get_for_model(Pension)

            # 2. Statutory Pension Statements (DRV Renteninformation)
            drv_entries = data.get('drv_statements', [])
            if isinstance(drv_entries, list):
                for drv in drv_entries:
                    if not isinstance(drv, dict):
                        continue
                    provider_name = drv.get('provider') or f"Deutsche Rentenversicherung ({drv.get('person_name', p1_name)})"
                    pts_str = drv.get('pension_points')
                    pt_val_str = drv.get('point_value') or '39.32'
                    stand_today_str = drv.get('stand_today_net')
                    forecast_net_str = drv.get('forecast_net')
                    erwerbsminderung_str = drv.get('erwerbsminderung_net')
                    ret_age_str = drv.get('retirement_age') or profile.retirement_age
                    ret_date_str = drv.get('retirement_date')
                    statement_date_str = drv.get('statement_date')

                    pts = _to_decimal(pts_str)
                    pt_val = _to_decimal(pt_val_str) or Decimal('39.32')
                    expected_net = _to_decimal(forecast_net_str) or _to_decimal(stand_today_str)
                    em_net = _to_decimal(erwerbsminderung_str)

                    pension_id = drv.get('existing_pension_id')
                    pension = None
                    if pension_id:
                        pension = Pension.objects.filter(id=pension_id, user=user).first()
                    if not pension:
                        pension = Pension.objects.filter(user=user, provider=provider_name, pension_type='statutory').first()
                    if not pension:
                        pension = Pension(user=user, provider=provider_name, pension_type='statutory')

                    if pts is not None:
                        pension.pension_points = pts
                    pension.point_value = pt_val
                    if expected_net is not None:
                        pension.expected_payout_at_retirement = expected_net
                    if em_net is not None:
                        pension.disability_pension_net = em_net
                    try:
                        pension.retirement_age = int(ret_age_str) if ret_age_str else 67
                    except (ValueError, TypeError):
                        pension.retirement_age = 67

                    ret_d = _parse_date(ret_date_str)
                    if ret_d:
                        pension.start_payout_date = ret_d

                    notes_parts = []
                    if drv.get('versicherungsnummer'):
                        notes_parts.append(f"VS-Nr: {drv.get('versicherungsnummer')}")
                    if notes_parts:
                        pension.notes = " | ".join(notes_parts)

                    pension.save()

                    s_date = _parse_date(statement_date_str)
                    if s_date:
                        snap_net = _to_decimal(stand_today_str) or expected_net
                        existing_snaps = AssetSnapshot.objects.filter(user=user, content_type=ct_pension, object_id=pension.id)
                        latest_snap_date = existing_snaps.order_by('-date').values_list('date', flat=True).first()

                        if not latest_snap_date or s_date >= latest_snap_date:
                            if pts is not None:
                                pension.pension_points = pts
                            pension.point_value = pt_val
                            if expected_net is not None:
                                pension.expected_payout_at_retirement = expected_net
                            if em_net is not None:
                                pension.disability_pension_net = em_net
                            if ret_d:
                                pension.start_payout_date = ret_d
                            pension.save()

                        AssetSnapshot.objects.update_or_create(
                            user=user,
                            content_type=ct_pension,
                            object_id=pension.id,
                            date=s_date,
                            defaults={
                                'pension_points': pts,
                                'point_value': pt_val,
                                'expected_payout_net': snap_net,
                                'disability_pension_net': em_net,
                                'value': snap_net if snap_net else Decimal('0.00'),
                                'notes': f"Renteninformation Stand {s_date.strftime('%d.%m.%Y')}"
                            }
                        )

            # 3. Private & Occupational Pension Statements
            private_entries = data.get('private_statements', [])
            if isinstance(private_entries, list):
                for priv in private_entries:
                    if not isinstance(priv, dict):
                        continue
                    provider = str(priv.get('provider', 'Private Vorsorge')).strip()
                    policy_nr = str(priv.get('policy_number', '')).strip()
                    full_provider = f"{provider} (Pol.-Nr. {policy_nr})" if policy_nr else provider

                    cap_val_str = priv.get('current_capital') or priv.get('garantiekapital') or priv.get('rueckkaufswert')
                    expected_net_str = priv.get('expected_monthly_payout') or priv.get('garantierente')
                    contrib_str = priv.get('monthly_contribution')
                    growth_str = priv.get('growth_rate')
                    ret_date_str = priv.get('payout_start_date')
                    statement_date_str = priv.get('statement_date')

                    pension_id = priv.get('existing_pension_id')
                    pension = None
                    if pension_id:
                        pension = Pension.objects.filter(id=pension_id, user=user).first()
                    if not pension:
                        pension = Pension.objects.filter(user=user, provider=full_provider, pension_type='capital').first()
                    if not pension:
                        pension = Pension(user=user, provider=full_provider, pension_type='capital')

                    cap_val = _to_decimal(cap_val_str)
                    expected_net = _to_decimal(expected_net_str)
                    contrib = _to_decimal(contrib_str)
                    growth = _to_decimal(growth_str)
                    s_date = _parse_date(statement_date_str)
                    ret_d = _parse_date(ret_date_str)

                    existing_snaps = AssetSnapshot.objects.filter(user=user, content_type=ct_pension, object_id=pension.id) if pension.id else []
                    latest_snap_date = existing_snaps.order_by('-date').values_list('date', flat=True).first() if existing_snaps else None

                    if not s_date or not latest_snap_date or s_date >= latest_snap_date:
                        if cap_val is not None:
                            pension.current_value = cap_val
                        if expected_net is not None:
                            pension.expected_payout_at_retirement = expected_net
                        if contrib is not None:
                            pension.monthly_contribution = contrib
                        if growth is not None:
                            pension.growth_rate = growth
                        if ret_d:
                            pension.start_payout_date = ret_d

                    notes = []
                    if priv.get('garantiekapital'): notes.append(f"Garantiekapital: {priv.get('garantiekapital')} €")
                    if priv.get('todesfallleistung'): notes.append(f"Todesfallleistung: {priv.get('todesfallleistung')} €")
                    if notes: pension.notes = " | ".join(notes)

                    pension.save()

                    if s_date and cap_val is not None:
                        AssetSnapshot.objects.update_or_create(
                            user=user,
                            content_type=ct_pension,
                            object_id=pension.id,
                            date=s_date,
                            defaults={
                                'value': cap_val,
                                'expected_payout_net': expected_net,
                                'notes': f"Standmitteilung {s_date.strftime('%d.%m.%Y')}"
                            }
                        )

            # 4. Income & Expenses
            cat_gehalt = _get_category_by_slug_or_name('gehalt', 'Gehalt', '#11ff00')
            cat_leben = _get_category_by_slug_or_name('lebenshaltung', 'Lebenshaltung', '#fd7e14')
            cat_steuern = _get_category_by_slug_or_name('steuern-abgaben', 'Steuern & Abgaben', '#dc3545')

            incomes = data.get('incomes', [])
            if isinstance(incomes, list):
                for inc in incomes:
                    if not isinstance(inc, dict):
                        continue
                    amt = _to_decimal(inc.get('amount'))
                    name = str(inc.get('name', 'Gehalt / Einnahme')).strip()
                    if amt and amt > 0 and name:
                        CashFlowSource.objects.update_or_create(
                            user=user,
                            name=name,
                            is_income=True,
                            defaults={
                                'value': amt,
                                'frequency': inc.get('frequency', 'monthly'),
                                'category': cat_gehalt
                            }
                        )

            expenses = data.get('expenses', [])
            if isinstance(expenses, list):
                for exp in expenses:
                    if not isinstance(exp, dict):
                        continue
                    amt = _to_decimal(exp.get('amount'))
                    name = str(exp.get('name', 'Ausgabe')).strip()
                    if amt and amt > 0 and name:
                        cat_exp = cat_steuern if 'steuer' in name.lower() else cat_leben
                        CashFlowSource.objects.update_or_create(
                            user=user,
                            name=name,
                            is_income=False,
                            defaults={
                                'value': amt,
                                'frequency': exp.get('frequency', 'monthly'),
                                'category': cat_exp
                            }
                        )

            # 5. Liquid Assets
            assets = data.get('assets', [])
            if isinstance(assets, list):
                for ast in assets:
                    if not isinstance(ast, dict):
                        continue
                    amt = _to_decimal(ast.get('value'))
                    name = str(ast.get('name', 'Konto / Depot')).strip()
                    if amt and amt > 0 and name:
                        growth = _to_decimal(ast.get('growth_rate')) or Decimal('0.0')
                        Asset.objects.update_or_create(
                            user=user,
                            name=name,
                            defaults={
                                'value': amt,
                                'growth_rate': growth
                            }
                        )

            # 6. Real Estate & Mortgages
            real_estates = data.get('real_estates', [])
            if isinstance(real_estates, list):
                for re_item in real_estates:
                    if not isinstance(re_item, dict):
                        continue
                    prop_val = _to_decimal(re_item.get('property_value'))
                    name = str(re_item.get('name', 'Eigenheim / Immobilie')).strip()
                    if prop_val and prop_val > 0 and name:
                        apprec = _to_decimal(re_item.get('appreciation_rate')) or Decimal('1.5')
                        maint = _to_decimal(re_item.get('maintenance_monthly')) or Decimal('0.0')
                        ancill = _to_decimal(re_item.get('ancillary_monthly')) or Decimal('0.0')
                        RealEstate.objects.update_or_create(
                            user=user,
                            name=name,
                            defaults={
                                'property_value': prop_val,
                                'appreciation_rate': apprec,
                                'location': re_item.get('location', ''),
                                'maintenance_costs_monthly': maint,
                                'ancillary_costs_monthly': ancill
                            }
                        )

            loans = data.get('loans', [])
            if isinstance(loans, list):
                for ln in loans:
                    if not isinstance(ln, dict):
                        continue
                    nominal = _to_decimal(ln.get('nominal_amount'))
                    name = str(ln.get('name', 'Immobiliendarlehen')).strip()
                    if nominal and nominal > 0 and name:
                        installment = _to_decimal(ln.get('monthly_installment')) or Decimal('0.0')
                        rate = _to_decimal(ln.get('interest_rate')) or Decimal('2.0')
                        start_d = _parse_date(ln.get('start_date')) or date.today()
                        Loan.objects.update_or_create(
                            user=user,
                            name=name,
                            defaults={
                                'provider': ln.get('provider', ''),
                                'nominal_amount': nominal,
                                'interest_rate': rate,
                                'monthly_installment': installment,
                                'start_date': start_d
                            }
                        )

        messages.success(request, _('Finanzdaten und Stichtagsmitteilungen wurden erfolgreich gespeichert!'))
        return JsonResponse({'status': 'success', 'redirect_url': '/finance/pensions/'})

    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print("=== WIZARD SAVE ERROR LOG ===")
        print(tb_str)
        return JsonResponse({'status': 'error', 'message': f"{type(e).__name__}: {str(e)}", 'traceback': tb_str}, status=500)
