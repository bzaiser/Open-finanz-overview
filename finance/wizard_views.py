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
    
    # Pre-populate user contracts for document update selection
    pensions = Pension.objects.filter(user=request.user)
    pensions_data = []
    for p in pensions:
        pensions_data.append({
            'id': p.id,
            'provider': p.provider,
            'pension_type': p.pension_type,
            'pension_points': float(p.pension_points) if p.pension_points is not None else None,
            'point_value': float(p.point_value) if p.point_value is not None else 39.32,
            'expected_payout_at_retirement': float(p.expected_payout_at_retirement) if p.expected_payout_at_retirement is not None else None,
            'current_value': float(p.current_value) if p.current_value is not None else 0.0,
            'growth_rate': float(p.growth_rate) if p.growth_rate is not None else 0.0,
            'monthly_contribution': float(p.monthly_contribution) if p.monthly_contribution is not None else 0.0,
        })

    context = {
        'profile': profile,
        'categories': categories,
        'pensions_json': json.dumps(pensions_data),
    }
    return render(request, 'finance/setup_wizard.html', context)


@login_required
def wizard_save_api(request):
    """
    API endpoint that accepts the JSON payload from the wizard and creates/updates all financial objects.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # 1. Profile & Persons
        household_type = data.get('household_type', 'single') # 'single' or 'couple'
        p1_name = data.get('p1_name', '').strip() or user.first_name or "Person 1"
        p1_birth = data.get('p1_birth_date')
        p1_ret_age = data.get('p1_retirement_age')
        
        if p1_birth:
            profile.birth_date = datetime.strptime(p1_birth, '%Y-%m-%d').date()
        if p1_ret_age:
            profile.retirement_age = int(p1_ret_age)
        
        target_pension = data.get('target_monthly_payout')
        if target_pension:
            profile.target_pension_payout = Decimal(str(target_pension))
            
        profile.display_name = p1_name if household_type == 'single' else f"{p1_name} & {data.get('p2_name', 'Partner')}"
        profile.save()

        ct_pension = ContentType.objects.get_for_model(Pension)

        # 2. Statutory Pension Statements (DRV Renteninformation)
        drv_entries = data.get('drv_statements', [])
        for drv in drv_entries:
            provider_name = drv.get('provider') or f"Deutsche Rentenversicherung ({drv.get('person_name', p1_name)})"
            pts_str = drv.get('pension_points')
            pt_val_str = drv.get('point_value') or '39.32'
            stand_today_str = drv.get('stand_today_net') # Bislang erreichte Rentenanwartschaft
            forecast_net_str = drv.get('forecast_net') # Hochrechnung Regelaltersrente
            erwerbsminderung_str = drv.get('erwerbsminderung_net')
            ret_age_str = drv.get('retirement_age') or profile.retirement_age
            ret_date_str = drv.get('retirement_date') # Regelaltersrente am
            statement_date_str = drv.get('statement_date') # Stand vom

            pts = Decimal(str(pts_str)) if pts_str else None
            pt_val = Decimal(str(pt_val_str)) if pt_val_str else Decimal('39.32')
            expected_net = Decimal(str(forecast_net_str)) if forecast_net_str else (Decimal(str(stand_today_str)) if stand_today_str else None)

            # Match or create pension contract
            pension_id = drv.get('existing_pension_id')
            if pension_id:
                pension = Pension.objects.filter(id=pension_id, user=user).first()
            else:
                pension = Pension.objects.filter(user=user, provider=provider_name, pension_type='statutory').first()

            if not pension:
                pension = Pension(user=user, provider=provider_name, pension_type='statutory')

            if pts is not None:
                pension.pension_points = pts
            pension.point_value = pt_val
            if expected_net is not None:
                pension.expected_payout_at_retirement = expected_net
            pension.retirement_age = int(ret_age_str) if ret_age_str else 67

            if ret_date_str:
                pension.start_payout_date = datetime.strptime(ret_date_str, '%Y-%m-%d').date()

            notes_parts = []
            if erwerbsminderung_str:
                notes_parts.append(f"Erwerbsminderungsrente: {erwerbsminderung_str} €")
            if drv.get('versicherungsnummer'):
                notes_parts.append(f"VS-Nr: {drv.get('versicherungsnummer')}")
            if notes_parts:
                pension.notes = " | ".join(notes_parts)

            pension.save()

            # Record Snapshot if statement_date is present
            if statement_date_str:
                s_date = datetime.strptime(statement_date_str, '%Y-%m-%d').date()
                snap_net = Decimal(str(stand_today_str)) if stand_today_str else expected_net
                AssetSnapshot.objects.update_or_create(
                    user=user,
                    content_type=ct_pension,
                    object_id=pension.id,
                    date=s_date,
                    defaults={
                        'pension_points': pts,
                        'point_value': pt_val,
                        'expected_payout_net': snap_net,
                        'value': snap_net if snap_net else Decimal('0.00'),
                        'notes': f"Renteninformation Stand {s_date.strftime('%d.%m.%Y')}"
                    }
                )

        # 3. Private / Occupational Pension Statements (bAV, Riester, Allianz, etc.)
        private_entries = data.get('private_statements', [])
        for priv in private_entries:
            provider = priv.get('provider', 'Private Vorsorge')
            policy_nr = priv.get('policy_number', '')
            full_provider = f"{provider} (Pol.-Nr. {policy_nr})" if policy_nr else provider

            cap_val_str = priv.get('current_capital') or priv.get('garantiekapital') or priv.get('rueckkaufswert')
            expected_net_str = priv.get('expected_monthly_payout') or priv.get('garantierente')
            contrib_str = priv.get('monthly_contribution')
            growth_str = priv.get('growth_rate')
            ret_date_str = priv.get('payout_start_date')
            statement_date_str = priv.get('statement_date')

            pension_id = priv.get('existing_pension_id')
            if pension_id:
                pension = Pension.objects.filter(id=pension_id, user=user).first()
            else:
                pension = Pension.objects.filter(user=user, provider=full_provider, pension_type='capital').first()

            if not pension:
                pension = Pension(user=user, provider=full_provider, pension_type='capital')

            if cap_val_str:
                pension.current_value = Decimal(str(cap_val_str))
            if expected_net_str:
                pension.expected_payout_at_retirement = Decimal(str(expected_net_str))
            if contrib_str:
                pension.monthly_contribution = Decimal(str(contrib_str))
            if growth_str:
                pension.growth_rate = Decimal(str(growth_str))
            if ret_date_str:
                pension.start_payout_date = datetime.strptime(ret_date_str, '%Y-%m-%d').date()

            notes = []
            if priv.get('garantiekapital'): notes.append(f"Garantiekapital: {priv.get('garantiekapital')} €")
            if priv.get('todesfallleistung'): notes.append(f"Todesfallleistung: {priv.get('todesfallleistung')} €")
            if notes: pension.notes = " | ".join(notes)

            pension.save()

            if statement_date_str and cap_val_str:
                s_date = datetime.strptime(statement_date_str, '%Y-%m-%d').date()
                snap_val = Decimal(str(cap_val_str))
                AssetSnapshot.objects.update_or_create(
                    user=user,
                    content_type=ct_pension,
                    object_id=pension.id,
                    date=s_date,
                    defaults={
                        'value': snap_val,
                        'expected_payout_net': Decimal(str(expected_net_str)) if expected_net_str else None,
                        'notes': f"Standmitteilung {s_date.strftime('%d.%m.%Y')}"
                    }
                )

        # 4. Income & Expenses
        cat_gehalt = _get_category_by_slug_or_name('gehalt', 'Gehalt', '#11ff00')
        cat_leben = _get_category_by_slug_or_name('lebenshaltung', 'Lebenshaltung', '#fd7e14')
        cat_steuern = _get_category_by_slug_or_name('steuern-abgaben', 'Steuern & Abgaben', '#dc3545')

        incomes = data.get('incomes', [])
        for inc in incomes:
            if inc.get('amount') and float(inc.get('amount')) > 0:
                CashFlowSource.objects.create(
                    user=user,
                    name=inc.get('name', 'Gehalt / Einnahme'),
                    value=Decimal(str(inc.get('amount'))),
                    is_income=True,
                    frequency=inc.get('frequency', 'monthly'),
                    category=cat_gehalt
                )

        expenses = data.get('expenses', [])
        for exp in expenses:
            if exp.get('amount') and float(exp.get('amount')) > 0:
                cat_exp = cat_steuern if 'steuer' in exp.get('name', '').lower() else cat_leben
                CashFlowSource.objects.create(
                    user=user,
                    name=exp.get('name', 'Ausgabe'),
                    value=Decimal(str(exp.get('amount'))),
                    is_income=False,
                    frequency=exp.get('frequency', 'monthly'),
                    category=cat_exp
                )

        # 5. Liquid Assets (Konten / Depots)
        assets = data.get('assets', [])
        for ast in assets:
            if ast.get('value') and float(ast.get('value')) > 0:
                Asset.objects.create(
                    user=user,
                    name=ast.get('name', 'Konto / Depot'),
                    value=Decimal(str(ast.get('value'))),
                    growth_rate=Decimal(str(ast.get('growth_rate', '0.0')))
                )

        # 6. Real Estate & Mortgages
        real_estates = data.get('real_estates', [])
        for re_item in real_estates:
            if re_item.get('property_value') and float(re_item.get('property_value')) > 0:
                RealEstate.objects.create(
                    user=user,
                    name=re_item.get('name', 'Eigenheim / Immobilie'),
                    property_value=Decimal(str(re_item.get('property_value'))),
                    appreciation_rate=Decimal(str(re_item.get('appreciation_rate', '1.5'))),
                    location=re_item.get('location', ''),
                    maintenance_costs_monthly=Decimal(str(re_item.get('maintenance_monthly', '0.0'))),
                    ancillary_costs_monthly=Decimal(str(re_item.get('ancillary_monthly', '0.0')))
                )

        loans = data.get('loans', [])
        for ln in loans:
            if ln.get('nominal_amount') and float(ln.get('nominal_amount')) > 0:
                start_d = datetime.strptime(ln.get('start_date'), '%Y-%m-%d').date() if ln.get('start_date') else date.today()
                Loan.objects.create(
                    user=user,
                    name=ln.get('name', 'Immobiliendarlehen'),
                    provider=ln.get('provider', ''),
                    nominal_amount=Decimal(str(ln.get('nominal_amount'))),
                    interest_rate=Decimal(str(ln.get('interest_rate', '2.0'))),
                    monthly_installment=Decimal(str(ln.get('monthly_installment', '0.0'))),
                    start_date=start_d
                )

        messages.success(request, _('Finanzdaten und Stichtagsmitteilungen wurden erfolgreich gespeichert!'))
        return JsonResponse({'status': 'success', 'redirect_url': '/finance/pensions/'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
