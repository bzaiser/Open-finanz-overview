from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _, gettext as _eager
from django.contrib import messages
from .services import SimulationEngine
from .models import (
    Asset, CashFlowSource, OneTimeEvent, Pension, Category, 
    ImportBatch, PendingTransaction
)
from .forms import BankImportForm
from core.models import UserProfile
from .import_services import ExcelParserService
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.core.files.storage import default_storage
import json
import os
import datetime
import requests
from decimal import Decimal

@login_required
def ai_status(request):
    """Hidden diagnostic view to check AI key status."""
    groq_ok = bool(getattr(settings, 'GROQ_API_KEY', None))
    gemini_ok = bool(getattr(settings, 'GEMINI_API_KEY', None))
    
    groq_ping = "N/A"
    if groq_ok:
        try:
            r = requests.get("https://api.groq.com/openai/v1/models", 
                             headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                             timeout=5)
            groq_ping = "Online" if r.status_code == 200 else f"Error {r.status_code}"
        except:
            groq_ping = "Offline"

    return render(request, 'finance/ai_status.html', {
        'groq_ok': groq_ok,
        'gemini_ok': gemini_ok,
        'groq_ping': groq_ping,
        'debug_mode': settings.DEBUG
    })
import threading
import time
from django.core.cache import cache
from decimal import Decimal

# Define available charts and their default properties
AVAILABLE_CHARTS = {
    'net_worth_chart': {'title': _('Net Worth Forecast'), 'type': 'line', 'default_width': 12, 'default_height': 'medium'},
    'cashflow_chart': {'title': _('Cash Flow Analysis'), 'type': 'bar', 'default_width': 6, 'default_height': 'small'},
    'income_evolution_chart': {'title': _('Income & One-Time Effects'), 'type': 'bar', 'default_width': 12, 'default_height': 'medium'},
    'expense_evolution_chart': {'title': _('Expense Evolution'), 'type': 'line', 'default_width': 6, 'default_height': 'small'},
    'inflation_monitor_chart': {'title': _('Inflation Monitor'), 'type': 'line', 'default_width': 6, 'default_height': 'small'},
    'budget_pie_chart': {'title': _('Monthly Budget'), 'type': 'pie', 'default_width': 6, 'default_height': 'small'},
    'asset_allocation_chart': {'title': _('Asset Allocation'), 'type': 'doughnut', 'default_width': 6, 'default_height': 'small'},
    'income_table_widget': {'title': _('Income Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'expense_table_widget': {'title': _('Expense Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'asset_table_widget': {'title': _('Asset Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'pension_table_widget': {'title': _('Pension Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'event_table_widget': {'title': _('One-Time Event Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
}

SUMMARY_WIDGETS = {
    'current_assets': {'title': _('Current Assets'), 'default_bg': '#0d6efd', 'default_text': '#ffffff'},
    'monthly_income': {'title': _('Monthly Income'), 'default_bg': '#198754', 'default_text': '#ffffff'},
    'monthly_expenses': {'title': _('Monthly Expenses'), 'default_bg': '#dc3545', 'default_text': '#ffffff'},
    'total_pensions': {'title': _('Pension Capital'), 'default_bg': '#0dcaf0', 'default_text': '#ffffff'},
    'expected_payout': {'title': _('Target Monthly Pension'), 'default_bg': '#6f42c1', 'default_text': '#ffffff'},
    'current_pension_payout': {'title': _('Current Pension'), 'default_bg': '#fd7e14', 'default_text': '#ffffff'},
}

DEFAULT_LAYOUT = [
    {'id': 'net_worth_chart', 'width': 12, 'height': 'medium', 'visible': True, 'order': 1, 'bg_color': '#ffffff', 'text_color': '#212529'},
    {'id': 'cashflow_chart', 'width': 6, 'height': 'small', 'visible': True, 'order': 2, 'bg_color': '#ffffff', 'text_color': '#212529'},
    {'id': 'income_evolution_chart', 'width': 12, 'height': 'medium', 'visible': True, 'order': 3, 'bg_color': '#ffffff', 'text_color': '#212529'},
    {'id': 'expense_evolution_chart', 'width': 6, 'height': 'small', 'visible': True, 'order': 4, 'bg_color': '#ffffff', 'text_color': '#212529'},
]

@login_required
def dashboard_view(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Helper for safe merging of defaults
    def safe_merge(user_data, defaults):
        if not user_data: return defaults
        return {**defaults, **user_data}

    # 0. Ensure specific categories exist for the split pension view
    Category.objects.get_or_create(name=str(_('Gesetzliche Rente')), defaults={'color': '#0d6efd', 'slug': 'gesetzliche-rente'})
    Category.objects.get_or_create(name=str(_('Private Kapital-Rente')), defaults={'color': '#0dcaf0', 'slug': 'private-kapital-rente'})

    # Initialize or get Dashboard Config
    dashboard_config = profile.dashboard_config or {}
    
    # 2. Extract configurations with safe defaults
    layout = dashboard_config.get('layout', DEFAULT_LAYOUT)

    summary_layout = dashboard_config.get('summary_layout', [
        {'id': 'current_assets', 'visible': True, 'bg_color': '#0d6efd', 'text_color': '#ffffff', 'order': 1},
        {'id': 'monthly_income', 'visible': True, 'bg_color': '#198754', 'text_color': '#ffffff', 'order': 2},
        {'id': 'monthly_expenses', 'visible': True, 'bg_color': '#dc3545', 'text_color': '#ffffff', 'order': 3},
        {'id': 'current_pension_payout', 'visible': True, 'bg_color': '#fd7e14', 'text_color': '#ffffff', 'order': 4},
        {'id': 'total_pensions', 'visible': True, 'bg_color': '#0dcaf0', 'text_color': '#ffffff', 'order': 5},
        {'id': 'expected_payout', 'visible': True, 'bg_color': '#6f42c1', 'text_color': '#ffffff', 'order': 6},
    ])

    # Ensure all available summary widgets are in the layout (auto-add missing ones)
    existing_ids = [item['id'] for item in summary_layout]
    for widget_id, widget_info in SUMMARY_WIDGETS.items():
        if widget_id not in existing_ids:
            summary_layout.append({
                'id': widget_id,
                'visible': False, 
                'bg_color': widget_info.get('default_bg', '#ffffff'),
                'text_color': widget_info.get('default_text', '#212529'),
                'order': len(summary_layout) + 1
            })

    simulation_config = safe_merge(dashboard_config.get('simulation_panel'), {
        'bg_color': '#ffffff', 
        'text_color': '#212529',
        'header_bg_color': '#ffc107',
        'header_text_color': '#212529'
    })

    table_config = safe_merge(dashboard_config.get('table_style'), {
        'header_bg_color': '#212529', 
        'header_text_color': '#ffffff',
        'filter_bg_color': '#f1f3f5',
        'body_bg_color': '#ffffff',
        'body_text_color': '#212529',
        'border_color': '#dee2e6',
    })
    
    # Remove old widgets that no longer exist
    layout = [item for item in layout if item['id'] not in ('net_worth_widget', 'projected_wealth_widget')]
    
    # Ensure all available charts are in the layout (if new ones added)
    existing_ids = [item['id'] for item in layout]
    for char_id, char_def in AVAILABLE_CHARTS.items():
        if char_id not in existing_ids:
            layout.append({
                'id': char_id, 
                'width': char_def['default_width'], 
                'height': char_def['default_height'], 
                'visible': False, 
                'order': 99,
                'bg_color': '#ffffff',
                'text_color': '#212529'
            })
            
    # Sort by order
    layout.sort(key=lambda x: x.get('order', 99))
    summary_layout.sort(key=lambda x: x.get('order', 99))

    # Simulation Params from Profile (with safe fallbacks for missing columns or NULL values)
    def get_safe_profile_val(profile_obj, field, default):
        val = getattr(profile_obj, field, default)
        if val is None:
            return float(default)
        return float(val)

    profile_params = {
        'inflation_rate': get_safe_profile_val(profile, 'inflation_rate', 2.0),
        'salary_increase': get_safe_profile_val(profile, 'salary_increase', 1.5),
        'pension_increase': get_safe_profile_val(profile, 'pension_increase', 1.0),
        'investment_return_offset': get_safe_profile_val(profile, 'investment_return_offset', 0.0),
    }
    
    simulation_params = profile_params.copy()
    stichtag_raw = request.GET.get('stichtag') or request.POST.get('stichtag')
    if stichtag_raw:
        try:
            simulation_params['stichtag'] = datetime.datetime.strptime(stichtag_raw, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            simulation_params['stichtag'] = timezone.now().date()
    else:
        simulation_params['stichtag'] = timezone.now().date()

    if request.method == 'POST':
        if 'config_update' in request.POST:
            # Handle Configuration Update
            try:
                if request.POST.get('layout_json'):
                    dashboard_config['layout'] = json.loads(request.POST.get('layout_json'))
                if request.POST.get('summary_layout_json'):
                    dashboard_config['summary_layout'] = json.loads(request.POST.get('summary_layout_json'))
                if request.POST.get('simulation_panel_json'):
                    dashboard_config['simulation_panel'] = json.loads(request.POST.get('simulation_panel_json'))
                if request.POST.get('table_style_json'):
                    dashboard_config['table_style'] = json.loads(request.POST.get('table_style_json'))
                
                profile.dashboard_config = dashboard_config
                profile.save()
                return redirect('dashboard')
            except json.JSONDecodeError:
                pass
        else:
            # Handle Simulation Update
            def safe_float(val, default):
                try: return float(val) if val else default
                except (ValueError, TypeError): return default
                    
            simulation_params['inflation_rate'] = safe_float(request.POST.get('inflation_rate'), profile_params['inflation_rate'])
            simulation_params['salary_increase'] = safe_float(request.POST.get('salary_increase'), profile_params['salary_increase'])
            simulation_params['investment_return_offset'] = safe_float(request.POST.get('investment_return_offset'), profile_params['investment_return_offset'])

    # Check if simulation is active (different from profile defaults)
    is_simulation_active = any(
        simulation_params[k] != profile_params[k] 
        for k in profile_params
    )

    # Charts affected by simulation
    affected_charts = ['net_worth_chart', 'cashflow_chart', 'income_evolution_chart', 'expense_evolution_chart', 'inflation_monitor_chart']

    engine = SimulationEngine(user, simulation_params)
    forecast_data = engine.get_forecast()
    
    # Prepare Chart Data
    yearly_buckets = {}
    
    # 1. Aggregate everything by year
    for d in forecast_data:
        year = d['date'].year
        if year not in yearly_buckets:
            yearly_buckets[year] = {
                'date': d['date'], # Sample date for month/day checks
                'nominal_net_worth': 0,
                'real_net_worth': 0,
                'monthly_income': 0,
                'monthly_expenses': 0,
                'one_time_events': [],
                'one_time_total': 0,
                'category_breakdown': {},
                'income_category_breakdown': {},
            }
        
        bucket = yearly_buckets[year]
        # Net worth is a point-in-time value, take the last one of the year
        bucket['nominal_net_worth'] = d['nominal_net_worth']
        bucket['real_net_worth'] = d['real_net_worth']
        
        # Totals for the year
        bucket['monthly_income'] += d['monthly_income']
        bucket['monthly_expenses'] += d['monthly_expenses']
        
        # Category Breakdowns (Sum up)
        for cat, val in d['category_breakdown'].items():
            bucket['category_breakdown'][cat] = bucket['category_breakdown'].get(cat, 0) + val
        for cat, val in d['income_category_breakdown'].items():
            bucket['income_category_breakdown'][cat] = bucket['income_category_breakdown'].get(cat, 0) + val
            
        # One Time Events
        if d['one_time_events']:
            bucket['one_time_events'].extend(d['one_time_events'])
            bucket['one_time_total'] += sum(evt['value'] for evt in d['one_time_events'])

    sorted_years = sorted(yearly_buckets.keys())
    
    labels_yearly = []
    net_worth_nominal = []
    net_worth_real = []
    income_yearly = []
    expenses_yearly = []
    net_savings_yearly = []
    one_time_yearly = []
    one_time_tooltips = []
    
    birth_date = profile.birth_date

    for year in sorted_years:
        bucket = yearly_buckets[year]
        d_date = bucket['date']
        
        # Label with Age
        label = str(year)
        if birth_date:
            age = year - birth_date.year - ((d_date.month, d_date.day) < (birth_date.month, birth_date.day))
            label = f"{year} ({age})"
        labels_yearly.append(label)
        
        net_worth_nominal.append(float(bucket['nominal_net_worth']))
        net_worth_real.append(float(bucket['real_net_worth']))
        
        income_yearly.append(float(bucket['monthly_income']))
        expenses_yearly.append(-float(bucket['monthly_expenses']))
        net_savings_yearly.append(float(bucket['monthly_income'] - bucket['monthly_expenses'] + bucket['one_time_total']))
        
        one_time_yearly.append(float(bucket['one_time_total']))
        one_time_tooltips.append(bucket['one_time_events'])

    # Categories for stacked charts
    income_categories = set()
    expense_categories = set()
    for year in sorted_years:
        income_categories.update(yearly_buckets[year]['income_category_breakdown'].keys())
        expense_categories.update(yearly_buckets[year]['category_breakdown'].keys())
    
    category_color_map = {c.name: c.color for c in Category.objects.all()}
    fallback_colors = ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0']

    income_evo_datasets = []
    for idx, cat in enumerate(sorted(list(income_categories))):
        cat_data = [float(yearly_buckets[y]['income_category_breakdown'].get(cat, 0)) for y in sorted_years]
        color = category_color_map.get(cat, fallback_colors[idx % len(fallback_colors)])
        income_evo_datasets.append({
            'label': cat,
            'data': cat_data,
            'backgroundColor': color,
            'stack': 'income',
        })
    
    expense_evo_datasets = []
    for idx, cat in enumerate(sorted(list(expense_categories))):
        cat_data = [float(yearly_buckets[y]['category_breakdown'].get(cat, 0)) for y in sorted_years]
        color = category_color_map.get(cat, fallback_colors[idx % len(fallback_colors)])
        expense_evo_datasets.append({
            'label': cat,
            'data': cat_data,
            'backgroundColor': color,
            'borderColor': '#000000',
            'borderWidth': 1.5,
            'pointBackgroundColor': color,
            'pointBorderColor': '#000000',
            'fill': True
        })

    # Add One-Time Events to Income Evolution chart
    income_evo_datasets.append({
        'label': str(_('One-Time Events')),
        'data': one_time_yearly,
        'backgroundColor': 'rgba(255, 165, 0, 0.85)',
        'borderColor': '#ff8c00',
        'borderWidth': 2,
        'stack': 'events',
        'tooltipData': one_time_tooltips,
    })

    # 3. Budget Pie & Current Month Data (Reference month breakdown)
    stichtag_val = simulation_params.get('stichtag')
    try:
        if isinstance(stichtag_val, str):
            target_date = datetime.datetime.strptime(stichtag_val, '%Y-%m-%d').date().replace(day=1)
        elif hasattr(stichtag_val, 'year'):
            target_date = stichtag_val.replace(day=1)
        else:
            target_date = timezone.now().date().replace(day=1)
    except:
        target_date = timezone.now().date().replace(day=1)

    # Find the forecast entry closest to target_date (avoids exact-match failures)
    current_month_data = min(forecast_data, key=lambda d: abs((d['date'] - target_date).days))
            
    budget_labels = list(current_month_data['category_breakdown'].keys())
    budget_data = list(current_month_data['category_breakdown'].values())
    budget_colors = [category_color_map.get(lbl, fallback_colors[i % len(fallback_colors)]) for i, lbl in enumerate(budget_labels)]

    # 5. Inflation Monitor (Real vs Nominal Gap + Lines)
    inflation_loss = []
    inflation_loss_percent = []
    for y in sorted_years:
        bucket = yearly_buckets[y]
        nom = float(bucket['nominal_net_worth'])
        real = float(bucket['real_net_worth'])
        loss = nom - real
        inflation_loss.append(loss)
        if nom > 0:
            percent = (loss / nom) * 100
        else:
            percent = 0.0
        inflation_loss_percent.append(percent)

    # Identify the index of the Stichtag's year for highlighting in charts
    stichtag_year = target_date.year
    stichtag_year_index = -1
    for i, yr in enumerate(sorted_years):
        if yr == stichtag_year:
            stichtag_year_index = i
            break

    inflation_data = {
        'labels': labels_yearly,
        'nominal': net_worth_nominal,
        'real': net_worth_real,
        'loss': inflation_loss,
        'loss_percent': inflation_loss_percent,
        'stichtag_index': stichtag_year_index
    }

    # Force language activation for chart data to ensure consistent translation
    with translation.override(translation.get_language()):
        chart_datasets = {
            'net_worth_chart': {
                'labels': labels_yearly,
                'datasets': [
                    {'label': _eager('Nominal'), 'data': net_worth_nominal, 'borderColor': 'blue', 'fill': True},
                    {'label': _eager('Real'), 'data': net_worth_real, 'borderColor': 'green', 'borderDash': [5, 5], 'fill': False},
                ],
                'stichtag_index': stichtag_year_index
            },
            'cashflow_chart': {
                 'labels': labels_yearly,
                 'datasets': [
                     {'label': _eager('Income'), 'data': income_yearly, 'backgroundColor': 'rgba(25, 135, 84, 0.7)', 'order': 2},
                     {'label': _eager('Expenses'), 'data': expenses_yearly, 'backgroundColor': 'rgba(220, 53, 69, 0.7)', 'order': 2},
                     {'label': _eager('Net Savings'), 'data': net_savings_yearly, 'type': 'line', 'borderColor': '#0d6efd', 'borderWidth': 2, 'fill': False, 'pointRadius': 3, 'order': 1},
                 ]
            },
            'income_evolution_chart': {
                'labels': labels_yearly,
                'datasets': income_evo_datasets,
            },
            'expense_evolution_chart': {
                'labels': labels_yearly,
                'datasets': expense_evo_datasets
            },
            'budget_pie_chart': {
                'labels': budget_labels,
                'datasets': [{'data': budget_data, 'backgroundColor': budget_colors}]
            },
            'inflation_monitor_chart': {
                'labels': labels_yearly,
                'datasets': [
                    {'label': _eager('Nominal Value'), 'data': net_worth_nominal, 'borderColor': '#0d6efd', 'fill': False},
                    {'label': _eager('Real Value (Purchasing Power)'), 'data': net_worth_real, 'borderColor': '#198754', 'fill': False},
                    {
                        'label': _eager('Purchasing Power Loss'), 
                        'data': inflation_loss, 
                        'backgroundColor': 'rgba(220, 53, 69, 0.5)', 
                        'type': 'bar',
                        'percentData': inflation_loss_percent
                    }
                ]
            },
            'asset_allocation_chart': {
                'labels': [
                    _eager('Liquid Assets'),
                    _eager('Pension Capital'),
                    _eager('Accumulated Cash'),
                ],
                'datasets': [{
                    'data': [
                        round(current_month_data.get('real_asset_total', 0), 2),
                        round(current_month_data.get('real_pension_total', 0), 2),
                        round(current_month_data.get('real_accumulated_cash', 0), 2),
                    ],
                    'backgroundColor': ['#0d6efd', '#6f42c1', '#198754'],
                    'hoverOffset': 8,
                }]
            },
        }

    # Key Metrics for Summary Panels (Use REAL values for purchasing power consistency)
    last_month = forecast_data[-1]
    current_net_worth = round(current_month_data.get('real_net_worth', current_month_data.get('nominal_net_worth', 0)), 2)
    projected_net_worth = round(last_month.get('real_net_worth', last_month.get('nominal_net_worth', 0)), 2)
    current_monthly_income = round(current_month_data.get('monthly_income', 0), 2)       # Nominal: what you'll actually earn
    current_monthly_expenses = round(current_month_data.get('monthly_expenses', 0), 2)   # Nominal: what you'll actually spend
    current_pensions_total = round(current_month_data.get('real_pension_total', 0), 2)
    current_assets_total = round(current_month_data.get('real_asset_total', 0) + current_pensions_total, 2)
    
    # Calculate Total Expected Payout (Real value at Stichtag)
    raw_expected_sum = sum(p.expected_payout_at_retirement or 0 for p in user.pensions.all())
    
    # Calculate the adjustment growth factor from today to the Stichtag
    inflation_rate = Decimal(str(simulation_params.get('inflation_rate', profile.inflation_rate))) / 100
    stichtag_dt = simulation_params['stichtag']
    if isinstance(stichtag_dt, str):
        stichtag_dt = datetime.datetime.strptime(stichtag_dt, '%Y-%m-%d').date()
    
    today = timezone.now().date()
    
    # Calculate months from today to Stichtag for growth factor
    months_diff = (stichtag_dt.year - today.year) * 12 + (stichtag_dt.month - today.month)
    years_diff_decimal = Decimal(str(max(0, months_diff))) / 12
    growth_factor = (1 + inflation_rate) ** years_diff_decimal
    
    # Calculate adjustment factor for the target sum (if pensions not yet flowing)
    stichtag_dt = simulation_params['stichtag']
    if isinstance(stichtag_dt, str):
        stichtag_dt = datetime.datetime.strptime(stichtag_dt, '%Y-%m-%d').date()
    today = timezone.now().date()
    months_diff = (stichtag_dt.year - today.year) * 12 + (stichtag_dt.month - today.month)
    inflation_rate = Decimal(str(simulation_params.get('inflation_rate', profile.inflation_rate))) / 100
    inflation_factor = (1 + inflation_rate) ** (Decimal(str(max(0, months_diff))) / 12)
    
    simulated_real_payout = current_month_data.get('real_monthly_pension_payout', 0)
    
    # We strictly show the actual simulated cashflow at the Stichtag
    # (If not retired at Stichtag, it will correctly show 0)
    total_expected_pensions = simulated_real_payout
    
    simulated_end_age = int(profile.simulation_max_age)
    
    # 7. Table Gadget Data (Monthly Normalized)
    continuous_label = _('Continuous')
    # 7. Dynamic Table Widgets (Filtered by target_date)
    continuous_label = _('Continuous')
    table_data_income = []
    
    # 1. Manual Cash Flows
    for cf in user.cash_flows.select_related('category').filter(is_income=True):
        if (not cf.start_date or cf.start_date.replace(day=1) <= target_date) and \
           (not cf.end_date or cf.end_date.replace(day=1) >= target_date):
            amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
            table_data_income.append({
                'name': cf.name, 
                'amount': float(amt), 
                'category': cf.category.name if cf.category else _('Einnahme'),
                'type': _('Manuell'),
                'year': str(cf.start_date.year) if cf.start_date else continuous_label
            })
    
    # 2. Asset withdrawals (Income)
    for a in user.assets.all():
        if a.withdrawal_start_date and a.withdrawal_start_date.replace(day=1) <= target_date:
            table_data_income.append({
                'name': f"{_('Entnahme')}: {a.name}", 
                'amount': float(a.withdrawal_amount or 0), 
                'category': _('Vermögen'),
                'type': _('Simulation'),
                'year': str(a.withdrawal_start_date.year)
            })

    # 3. Pension payouts (Income)
    for p in user.pensions.all():
        if p.start_payout_date and p.start_payout_date.replace(day=1) <= target_date:
            table_data_income.append({
                'name': f"{_('Rente')}: {p.provider}", 
                'amount': float(p.expected_payout_at_retirement or 0), 
                'category': _('Rente'),
                'type': _('Vertrag'),
                'year': str(p.start_payout_date.year)
            })

    table_data_expense = []
    # 1. Manual Cash Flows
    for cf in user.cash_flows.select_related('category').filter(is_income=False):
        if (not cf.start_date or cf.start_date.replace(day=1) <= target_date) and \
           (not cf.end_date or cf.end_date.replace(day=1) >= target_date):
            amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
            table_data_expense.append({
                'name': cf.name, 
                'amount': float(amt), 
                'category': cf.category.name if cf.category else _('Ausgabe'),
                'type': _('Manuell'),
                'year': str(cf.start_date.year) if cf.start_date else continuous_label
            })

    # 2. Pension contributions (Expense)
    for p in user.pensions.all():
        if p.monthly_contribution and p.monthly_contribution > 0:
            if not p.contribution_end_date or p.contribution_end_date.replace(day=1) > target_date:
                table_data_expense.append({
                    'name': f"{_('Beitrag')}: {p.provider}", 
                    'amount': float(p.monthly_contribution or 0), 
                    'category': _('Sparen'),
                    'type': _('Vertrag'),
                    'year': str(p.contribution_end_date.year) if p.contribution_end_date else continuous_label
                })

    table_data_asset = []
    for a in user.assets.all():
        table_data_asset.append({
            'name': a.name, 
            'amount': float(a.value or 0), 
            'category': _('Asset'),
            'rate': f"{a.growth_rate or 0}%",
            'year': continuous_label
        })

    for p in user.pensions.all():
        table_data_asset.append({
            'name': f"{_('Rente')}: {p.provider}", 
            'amount': float(p.current_value or 0), 
            'category': _('Rente'),
            'rate': f"{p.growth_rate or 0}%",
            'year': continuous_label
        })

    table_data_pension = []
    for p in user.pensions.all():
        year = str(p.start_payout_date.year) if p.start_payout_date else continuous_label
        table_data_pension.append({
            'name': p.provider, 
            'amount': float(p.current_value or 0), 
            'category': _('Rente'),
            'contribution': float(p.monthly_contribution or 0),
            'year': year
        })

    table_data_event = []
    for e in user.events.all():
        table_data_event.append({
            'name': e.name, 
            'amount': float(e.value), 
            'category': _('One-Time'),
            'date': e.date.strftime('%d.%m.%Y'),
            'year': str(e.date.year)
        })

    table_datasets = {
        'income_table_widget': table_data_income,
        'expense_table_widget': table_data_expense,
        'asset_table_widget': table_data_asset,
        'pension_table_widget': table_data_pension,
        'event_table_widget': table_data_event,
    }
    table_json = {k: json.dumps(v, cls=DjangoJSONEncoder) for k, v in table_datasets.items()}

    # Key Metrics for Summary Panels

    # Ensure all chart titles are eagerly translated in the current language context
    with translation.override(translation.get_language()):
        translated_available_charts = {k: {**v, 'title': _eager(str(v['title']))} for k, v in AVAILABLE_CHARTS.items()}
        translated_summary_widgets = {k: {**v, 'title': _eager(str(v['title']))} for k, v in SUMMARY_WIDGETS.items()}

    context = {
        'profile': profile,
        'currency': profile.currency or 'EUR',
        'layout': layout,
        'summary_layout': summary_layout,
        'layout_json': json.dumps(layout, cls=DjangoJSONEncoder),
        'summary_layout_json': json.dumps(summary_layout, cls=DjangoJSONEncoder),
        'available_charts': translated_available_charts,
        'summary_widgets': translated_summary_widgets,
        'chart_datasets': chart_datasets,
        'simulation_params': simulation_params,
        'is_simulation_active': is_simulation_active,
        'affected_charts': json.dumps(affected_charts),
        'current_net_worth': current_net_worth,
        'projected_net_worth': projected_net_worth,
        'simulated_end_age': simulated_end_age,
        'current_assets_total': current_assets_total,
        'current_monthly_income': current_monthly_income,
        'current_monthly_expenses': current_monthly_expenses,
        'current_pensions_total': current_pensions_total,
        'total_expected_pensions': raw_expected_sum, # The raw target sum from contracts
        'simulated_pension_payout': total_expected_pensions, # The actual simulated payout at Stichtag
        'stichtag_year_index': stichtag_year_index,
        'simulation_config': simulation_config,
        'table_config': table_config,
        'table_datasets': table_datasets,
        'debug_lang': translation.get_language(),
        'debug_trans_test': translation.gettext('Help'),
    }
    
    if request.headers.get('HX-Request'):
        from django.template.loader import render_to_string
        charts_html = render_to_string('finance/partials/dashboard_charts.html', context, request=request)
        summary_html = render_to_string('finance/partials/dashboard_summary.html', context, request=request)
        return HttpResponse(charts_html + summary_html)
        
    return render(request, 'finance/dashboard.html', context)


def _async_import_task(batch_id, file_path, filename):
    """
    Background worker that performs the long-running AI categorization.
    """
    # Give the main request a moment to finish its DB commit
    time.sleep(0.5)
    
    from django.db import connections
    from .models import ImportBatch
    from .import_services import ExcelParserService
    import logging
    
    logger = logging.getLogger(__name__)

    try:
        # Re-fetch the batch to ensure we have the latest state
        batch = ImportBatch.objects.get(id=batch_id)
        user = batch.user
        service = ExcelParserService(user, file_path, filename)
        service.parse_and_categorize(batch=batch)

        # Mark as 100% only AFTER everything is done and saved
        cache_key_progress = f"import_progress_{batch.user.id}"
        cache.set(cache_key_progress, 100, 300) # 5 minutes timeout
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_detailed = f"Kritischer Fehler: {str(e)}\n\nDetails:\n{error_trace}"
        logger.error(error_detailed)
        try:
            batch = ImportBatch.objects.get(id=batch_id)
            batch.ai_log = error_detailed
            batch.save()
            
            # Save the error to cache so the UI shows the TRACEBACK
            cache_key_progress = f"import_progress_{batch.user.id}"
            cache_key_error = f"import_error_{batch.user.id}"
            cache.set(cache_key_progress, -1, 300)
            cache.set(cache_key_error, error_detailed, 300)
        except:
            pass
    finally:
        for conn in connections.all():
            conn.close()

@login_required
def upload_bank_transactions(request):
    if request.method == 'POST':
        # 0. Cleanup old unapplied batches - gracefully
        try:
            cutoff = timezone.now() - datetime.timedelta(hours=24)
            ImportBatch.objects.filter(user=request.user, is_applied=False, date__lt=cutoff).delete()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cleanup of old batches failed: {e}")

        form = BankImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            
            # 1. Create the Batch synchronously so we have an ID
            batch = ImportBatch.objects.create(
                user=request.user, 
                filename=uploaded_file.name
            )

            # 2. Save file for the thread
            temp_subdir = os.path.join(settings.MEDIA_ROOT, 'temp_imports')
            os.makedirs(temp_subdir, exist_ok=True)
            file_path = os.path.join(temp_subdir, f"batch_{batch.id}_{int(time.time())}.xlsx")
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # 3. Reset progress and CLEAR previous errors
            cache_key_progress = f"import_progress_{request.user.id}"
            cache_key_error = f"import_error_{request.user.id}"
            cache.set(cache_key_progress, 0, 300)
            cache.delete(cache_key_error)

            # 4. Start background thread
            thread = threading.Thread(target=_async_import_task, args=(batch.id, file_path, uploaded_file.name))
            thread.daemon = True
            thread.start()

            return redirect('import_processing')
    else:
        form = BankImportForm()
    
    ai_active = bool(settings.GEMINI_API_KEY) or bool(getattr(settings, 'GROQ_API_KEY', None))
    return render(request, 'finance/import_upload.html', {
        'form': form,
        'ai_active': ai_active
    })

@login_required
def import_processing(request):
    # Find the latest unapplied batch
    latest_batch = ImportBatch.objects.filter(user=request.user, is_applied=False).order_by('-date').first()
    
    cache_key_progress = f"import_progress_{request.user.id}"
    cache_key_error = f"import_error_{request.user.id}"
    
    progress = cache.get(cache_key_progress, 0)
    error_msg = cache.get(cache_key_error, None)
    
    if progress >= 100 and latest_batch:
        return redirect('review_transactions', batch_id=latest_batch.id)
    
    # We no longer redirect immediately on -1 here, the template will handle it
    # to show the red box first!

    return render(request, 'finance/import_processing.html', {
        'progress': progress,
        'error_msg': error_msg,
        'batch': latest_batch
    })

@login_required
def review_bank_transactions(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    transactions = batch.transactions.all().order_by('date')
    categories = Category.objects.all()
    
    return render(request, 'finance/import_review.html', {
        'batch': batch,
        'transactions': transactions,
        'categories': categories,
        'ai_active': bool(settings.GEMINI_API_KEY or settings.GROQ_API_KEY)
    })

@login_required
def confirm_bank_transaction(request, transaction_id):
    """
    HTMX endpoint to toggle fields.
    """
    transaction = get_object_or_404(PendingTransaction, id=transaction_id, batch__user=request.user)
    
    field = request.GET.get('field')
    value = request.GET.get('value')
    
    if field == 'is_ignored':
        transaction.is_ignored = (value == 'true')
    elif field == 'is_recurring':
        transaction.is_recurring = (value == 'true')
    elif field == 'is_income':
        transaction.is_income = (value == 'true')
    elif field == 'category':
        transaction.category = Category.objects.filter(id=value).first()
    elif field == 'frequency':
        transaction.frequency = value
        
    transaction.save()
    
    # Return the partial for this row
    return render(request, 'finance/partials/import_row.html', {
        't': transaction, 
        'categories': Category.objects.all()
    })

@login_required
def apply_import_batch(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    if batch.is_applied:
        messages.warning(request, _("Dieser Import wurde bereits angewendet."))
        return redirect('dashboard')
        
    transactions = batch.transactions.filter(is_ignored=False)
    
    count_one_time = 0
    count_recurring = 0
    
    for t in transactions:
        if t.is_recurring:
            CashFlowSource.objects.create(
                user=request.user,
                name=t.description,
                value=t.amount if t.is_income else abs(t.amount),
                is_income=t.is_income,
                start_date=t.date,
                category=t.category,
                frequency=t.frequency,
                is_inflation_adjusted=True
            )
            count_recurring += 1
        else:
            OneTimeEvent.objects.create(
                user=request.user,
                name=t.description,
                value=t.amount if t.is_income else -abs(t.amount),
                date=t.date,
                description=_("Importiert via Bank-Assistent")
            )
            count_one_time += 1
            
    # Cleanup: Delete the batch and its pending transactions now that they are applied
    batch.delete()
    
    messages.success(request, _(f"Import abgeschlossen: {count_one_time} Einzelbuchungen und {count_recurring} regelmäßige Zahlungen erstellt."))
    return redirect('dashboard')

@login_required
def get_import_progress(request):
    """
    Returns the current import progress percentage AND the ai_log as HTML.
    Target for HTMX polling.
    """
    cache_key = f"import_progress_{request.user.id}"
    progress = cache.get(cache_key, 0)
    
    # Fetch the latest batch to get the REAL-TIME log
    latest_batch = ImportBatch.objects.filter(user=request.user, is_applied=False).order_by('-date').first()
    log_content = latest_batch.ai_log if latest_batch else "Warte auf Batch..."
    
    # We return the bar AND the updated log window content
    html = f'''
    <div class="progress" style="height: 25px;">
        <div class="progress-bar progress-bar-striped progress-bar-animated" 
             role="progressbar" 
             style="width: {progress}%;" 
             aria-valuenow="{progress}" 
             aria-valuemin="0" 
             aria-valuemax="100">
             {progress}%
        </div>
    </div>
    <p class="text-center mt-2 text-muted small">KI analysiert Daten... ({progress}%)</p>

    <!-- Update the log window via OOB (Out of Band) swap or just inclusion -->
    <div id="ai-log-stream" hx-swap-oob="innerHTML">
        {log_content.replace("\\n", "<br>")}
    </div>
    '''
    return HttpResponse(html)

@login_required
def delete_all_temporary_data(request):
    """
    Deletes all ImportBatch objects (and cascading PendingTransactions) 
    for the current user that haven't been applied yet.
    """
    batches = ImportBatch.objects.filter(user=request.user, is_applied=False)
    count = batches.count()
    batches.delete()
    
    # Also clear any stuck progress indicators in the cache
    cache_key = f"import_progress_{request.user.id}"
    cache.delete(cache_key)
    
    messages.success(request, _(f"{count} temporäre Import-Datensätze wurden gelöscht."))
    return redirect('import_transactions')
