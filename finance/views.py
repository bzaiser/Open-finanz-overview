from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _, gettext as _eager
from django.contrib import messages
from .services import SimulationEngine
from .models import (
    Asset, CashFlowSource, OneTimeEvent, Pension, Category, 
    ImportBatch, PendingTransaction, ImportFilter
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
    'loan_table_widget': {'title': _('Loan Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'loan_evolution_chart': {'title': _('Loan Balance Trend'), 'type': 'line', 'default_width': 12, 'default_height': 'medium'},
}

SUMMARY_WIDGETS = {
    'current_assets': {'title': _('Current Assets'), 'default_bg': '#0d6efd', 'default_text': '#ffffff', 'icon': 'bi-wallet2'},
    'monthly_income': {'title': _('Monthly Income'), 'default_bg': '#198754', 'default_text': '#ffffff', 'icon': 'bi-graph-up-arrow'},
    'monthly_expenses': {'title': _('Monthly Expenses'), 'default_bg': '#dc3545', 'default_text': '#ffffff', 'icon': 'bi-graph-down-arrow'},
    'total_pensions': {'title': _('Pension Capital'), 'default_bg': '#0dcaf0', 'default_text': '#ffffff', 'icon': 'bi-bank'},
    'expected_payout': {'title': _('Target Monthly Pension'), 'default_bg': '#6f42c1', 'default_text': '#ffffff', 'icon': 'bi-target'},
    'current_pension_payout': {'title': _('Current Pension'), 'default_bg': '#fd7e14', 'default_text': '#ffffff', 'icon': 'bi-cash-stack'},
    'total_physical_assets': {'title': _('Sachwerte'), 'default_bg': '#8a2be2', 'default_text': '#ffffff', 'icon': 'bi-car-front'},
    'total_real_estate': {'title': _('Immobilien'), 'default_bg': '#20c997', 'default_text': '#ffffff', 'icon': 'bi-house-heart'},
    'total_combined_assets': {'title': _('Gesamtvermögen'), 'default_bg': '#ffc107', 'default_text': '#212529', 'icon': 'bi-pie-chart'},
    'total_debts': {'title': _('Gesamtschulden'), 'default_bg': '#343a40', 'default_text': '#ffffff', 'icon': 'bi-credit-card-2-front'},
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
    Category.objects.get_or_create(slug='gesetzliche-rente', defaults={'name': _('Gesetzliche Rente'), 'color': '#0d6efd', 'is_system': True})
    Category.objects.get_or_create(slug='private-kapital-rente', defaults={'name': _('Private Kapital-Rente'), 'color': '#0dcaf0', 'is_system': True})

    # Initialize or get Dashboard Config
    dashboard_config = profile.dashboard_config or {}
    
    # 2. Extract configurations with safe defaults
    layout = dashboard_config.get('layout', DEFAULT_LAYOUT)

    summary_layout = dashboard_config.get('summary_layout', [
        {'id': 'current_assets', 'visible': True, 'bg_color': 'var(--app-primary)', 'text_color': '#ffffff', 'order': 1},
        {'id': 'monthly_income', 'visible': True, 'bg_color': '#198754', 'text_color': '#ffffff', 'order': 2},
        {'id': 'monthly_expenses', 'visible': True, 'bg_color': '#dc3545', 'text_color': '#ffffff', 'order': 3},
        {'id': 'current_pension_payout', 'visible': True, 'bg_color': '#fd7e14', 'text_color': '#ffffff', 'order': 4},
        {'id': 'total_pensions', 'visible': True, 'bg_color': '#0dcaf0', 'text_color': '#ffffff', 'order': 5},
        {'id': 'expected_payout', 'visible': True, 'bg_color': '#6f42c1', 'text_color': '#ffffff', 'order': 6},
        {'id': 'total_physical_assets', 'visible': True, 'bg_color': '#8a2be2', 'text_color': '#ffffff', 'order': 8},
        {'id': 'total_real_estate', 'visible': True, 'bg_color': '#20c997', 'text_color': '#ffffff', 'order': 9},
        {'id': 'total_combined_assets', 'visible': True, 'bg_color': 'var(--app-primary)', 'text_color': '#ffffff', 'order': 1},
    ])

    # Ensure all available summary widgets are in the layout (auto-add missing ones)
    existing_ids = [item['id'] for item in summary_layout]
    for widget_id, widget_info in SUMMARY_WIDGETS.items():
        if widget_id not in existing_ids:
            summary_layout.append({
                'id': widget_id,
                'visible': False, 
                'bg_color': 'var(--app-card-bg)',
                'text_color': 'var(--app-card-color)',
                'order': len(summary_layout) + 1
            })

    simulation_config = {
        'bg_color': profile.background_color or '#ffffff', 
        'text_color': profile.text_color or '#212529',
        'header_bg_color': profile.primary_color or '#0d6efd',
        'header_text_color': '#ffffff'
    }

    table_config = {
        'header_bg_color': profile.table_header_bg_color or 'var(--app-primary)', 
        'header_text_color': profile.table_header_text_color or '#ffffff',
        'filter_bg_color': profile.table_filter_bg_color or 'rgba(0,0,0,0.05)',
        'body_bg_color': profile.table_body_bg_color or 'var(--app-card-bg)',
        'body_text_color': profile.table_body_text_color or 'var(--app-card-color)',
        'border_color': profile.table_border_color or 'rgba(0,0,0,0.1)',
    }
    
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
        'real_estate_growth_rate': get_safe_profile_val(profile, 'real_estate_growth_rate', 0.0),
        'physical_asset_growth_rate': get_safe_profile_val(profile, 'physical_asset_growth_rate', 0.0),
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
            simulation_params['real_estate_growth_rate'] = safe_float(request.POST.get('real_estate_growth_rate'), profile_params['real_estate_growth_rate'])
            simulation_params['physical_asset_growth_rate'] = safe_float(request.POST.get('physical_asset_growth_rate'), profile_params['physical_asset_growth_rate'])

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
                'loan_total': 0,
                'loan_balances': {},
                'one_time_events': [],
                'one_time_total': 0,
                'category_breakdown': {},
                'income_category_breakdown': {},
            }
        
        bucket = yearly_buckets[year]
        # Net worth is a point-in-time value, take the last one of the year
        bucket['nominal_net_worth'] = d.get('nominal_net_worth', 0)
        bucket['real_net_worth'] = d.get('real_net_worth', 0)
        bucket['physical_asset_total'] = d.get('physical_asset_total', 0)
        bucket['real_estate_total'] = d.get('real_estate_total', 0)
        
        # Totals for the year
        bucket['monthly_income'] += d['monthly_income']
        bucket['monthly_expenses'] += d['monthly_expenses']
        bucket['loan_total'] = d.get('loan_total', 0) # Snap to last month of year
        bucket['one_time_total'] += d.get('one_time_impact', 0)
        
        # Category Breakdowns (Sum up)
        for cat, val in d['category_breakdown'].items():
            bucket['category_breakdown'][cat] = bucket['category_breakdown'].get(cat, 0) + val
        for cat, val in d['income_category_breakdown'].items():
            bucket['income_category_breakdown'][cat] = bucket['income_category_breakdown'].get(cat, 0) + val
            
        # Loan Balances (Snapshot at end of year)
        if 'loan_balances' in d:
            bucket['loan_balances'] = d['loan_balances']

        # One Time Events
        if d['one_time_events']:
            bucket['one_time_events'].extend(d['one_time_events'])
            bucket['one_time_total'] += sum(evt['value'] for evt in d['one_time_events'])

    sorted_years = sorted(yearly_buckets.keys())
    
    labels_yearly = []
    net_worth_nominal = []
    net_worth_real = []
    physical_asset_yearly = []
    real_estate_yearly = []
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
        physical_asset_yearly.append(float(bucket['physical_asset_total']))
        real_estate_yearly.append(float(bucket['real_estate_total']))
        
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

    # 2.2 Loan Evolution Chart
    loan_evo_datasets = []
    user_loans_list = list(user.loans.all())
    loan_colors = ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#0d6efd', '#6610f2', '#6f42c1', '#e83e8c']
    
    for idx, l in enumerate(user_loans_list):
        l_id_str = str(l.id)
        l_data = [float(yearly_buckets[y]['loan_balances'].get(l_id_str, 0)) for y in sorted_years]
        
        # Only add if there is any debt in the simulation period
        if any(v > 0 for v in l_data):
            loan_evo_datasets.append({
                'label': l.name,
                'data': l_data,
                'borderColor': loan_colors[idx % len(loan_colors)],
                'backgroundColor': loan_colors[idx % len(loan_colors)] + '1A', # 10% alpha
                'fill': False,
                'borderWidth': 3,
                'tension': 0.1
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
                    {'label': _eager('Nominal Gesamtwert'), 'data': net_worth_nominal, 'borderColor': 'blue'},
                    {'label': _eager('Real Gesamtwert'), 'data': net_worth_real, 'borderColor': 'green', 'borderDash': [5, 5]},
                    {'label': _eager('Sachwerte'), 'data': physical_asset_yearly, 'borderColor': '#8a2be2', 'backgroundColor': 'rgba(138, 43, 226, 0.1)', 'fill': True},
                    {'label': _eager('Immobilien'), 'data': real_estate_yearly, 'borderColor': '#20c997', 'backgroundColor': 'rgba(32, 201, 151, 0.1)', 'fill': True},
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
            'loan_evolution_chart': {
                'labels': labels_yearly,
                'datasets': loan_evo_datasets,
                'stichtag_index': stichtag_year_index
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
                    _eager('Sachwerte'),
                    _eager('Immobilien'),
                ],
                'datasets': [{
                    'data': [
                        round(current_month_data.get('real_asset_total', 0), 2),
                        round(current_month_data.get('real_pension_total', 0), 2),
                        round(current_month_data.get('real_accumulated_cash', 0), 2),
                        round(current_month_data.get('real_physical_asset_total', 0), 2),
                        round(current_month_data.get('real_real_estate_total', 0), 2),
                    ],
                    'backgroundColor': ['#0d6efd', '#6f42c1', '#198754', '#8a2be2', '#20c997'],
                    'hoverOffset': 8,
                }]
            },
        }

    # Key Metrics for Summary Panels (Use REAL values for purchasing power consistency)
    last_month = forecast_data[-1]
    current_net_worth = round(current_month_data.get('real_net_worth', current_month_data.get('nominal_net_worth', 0)), 2)
    projected_net_worth = round(last_month.get('real_net_worth', last_month.get('nominal_net_worth', 0)), 2)
    current_monthly_income = round(current_month_data.get('monthly_income', 0), 2)
    current_monthly_expenses = round(current_month_data.get('monthly_expenses', 0), 2)
    current_pensions_total = round(current_month_data.get('real_pension_total', 0), 2)
    current_assets_total = round(current_month_data.get('real_asset_total', 0) + current_pensions_total, 2)
    current_physical_assets_total = round(current_month_data.get('real_physical_asset_total', 0), 2)
    current_real_estate_total = round(current_month_data.get('real_real_estate_total', 0), 2)
    current_debts_total = round(current_month_data.get('real_loan_total', 0), 2)
    current_total_combined = round(current_assets_total + current_physical_assets_total + current_real_estate_total - current_debts_total, 2)
    
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

    # 3. Loan installments (Expense)
    for l in user.loans.all():
        l_state = next((item for item in forecast_data if item['date'] == target_date), None)
        if (not l.end_date or l.end_date.replace(day=1) >= target_date) and (l.start_date.replace(day=1) <= target_date):
            table_data_expense.append({
                'name': f"{_('Kreditrate')}: {l.name}", 
                'amount': float(l.monthly_installment), 
                'category': _('Kredit'),
                'type': _('Vertrag'),
                'year': str(l.end_date.year) if l.end_date else continuous_label
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

    table_data_loan = []
    loan_interest_map = getattr(engine, 'loan_interest_totals', {})

    for l in user.loans.all():
        l_id_str = str(l.id)
        # Remaining balance at Stichtag
        current_bal = current_month_data.get('loan_balances', {}).get(l_id_str, 0.0)
        total_int = loan_interest_map.get(l_id_str, 0.0)

        table_data_loan.append({
            'name': l.name,
            'amount': float(l.nominal_amount), 
            'current_balance': float(current_bal),
            'total_interest': float(total_int),
            'provider': l.provider,
            'rate': f"{l.interest_rate}%",
            'monthly': float(l.monthly_installment),
            'year': str(l.end_date.year) if l.end_date else continuous_label
        })

    table_datasets = {
        'income_table_widget': table_data_income,
        'expense_table_widget': table_data_expense,
        'asset_table_widget': table_data_asset,
        'pension_table_widget': table_data_pension,
        'event_table_widget': table_data_event,
        'loan_table_widget': table_data_loan,
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
        'current_physical_assets_total': current_physical_assets_total,
        'current_real_estate_total': current_real_estate_total,
        'current_debts_total': current_debts_total,
        'current_total_combined': current_total_combined,
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
    
    # We no longer redirect immediately on 100% here, the template will handle it
    # to show the button and message!
    
    return render(request, 'finance/import_processing.html', {
        'progress': progress,
        'error_msg': error_msg,
        'batch': latest_batch
    })

@login_required
def review_bank_transactions(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    
    # 1. Search Query for Mapping Pane
    q = request.GET.get('q', '').strip()
    
    # 2. Split into panes
    # Mapping: Not ignored, NO category
    mapping_qs = batch.transactions.filter(is_ignored=False, category__isnull=True)
    if q:
        mapping_qs = mapping_qs.filter(description__icontains=q)
    
    mapping_list = mapping_qs.order_by('date')
    
    # Ready: Not ignored, HAS category
    ready_list = batch.transactions.filter(is_ignored=False, category__isnull=False).order_by('date', '-amount')
    
    # Total sum for Ready Pane
    total_ready = sum(t.amount for t in ready_list)
    
    categories = Category.objects.all()
    filters = ImportFilter.objects.filter(user=request.user).order_by('target_name')
    
    # Check if this is an HTMX request for the Mapping Pane only
    if request.headers.get('HX-Request') and 'mapping-search' in request.GET.get('target', ''):
        return render(request, 'finance/partials/import_mapping_pane.html', {
            'transactions': mapping_list,
            'categories': categories,
            'batch': batch,  # Pass missing context
            'q': q
        })

    return render(request, 'finance/import_review.html', {
        'batch': batch,
        'mapping_list': mapping_list,
        'ready_list': ready_list,
        'total_ready': total_ready,
        'categories': categories,
        'filters': filters,
        'q': q,
        'ai_active': bool(settings.GEMINI_API_KEY or settings.GROQ_API_KEY)
    })

@login_required
def confirm_bank_transaction(request, transaction_id):
    """
    HTMX endpoint to toggle fields.
    Now supports moving rows between Mapping and Ready panes.
    """
    transaction = get_object_or_404(PendingTransaction, id=transaction_id, batch__user=request.user)
    
    field = request.GET.get('field')
    value = request.GET.get('value')
    
    was_mapping = (transaction.category is None and not transaction.is_ignored)
    
    if field == 'is_ignored':
        transaction.is_ignored = (value == 'true')
    elif field == 'is_recurring':
        transaction.is_recurring = (value == 'true')
    elif field == 'is_income':
        transaction.is_income = (value == 'true')
    elif field == 'category':
        transaction.category = Category.objects.filter(id=value).first()
        if transaction.category:
            transaction.is_ignored = False
    elif field == 'frequency':
        transaction.frequency = value
        
    transaction.save()
    
    is_mapping = (transaction.category is None and not transaction.is_ignored)
    is_ready = (transaction.category is not None and not transaction.is_ignored)
    
    categories = Category.objects.all()
    
    # If the state changed (mapping -> ready or vice versa), we might need to remove from one and add to another
    # Using HTMX Out-of-Band Swaps
    response_html = ""
    
    if is_mapping:
        # If it was in "Ready" before, we need a special OOB response to move it back
        if not was_mapping:
            response_html = f'<tr id="ready-row-{transaction.id}" hx-swap-oob="delete"></tr>'
            
            # Add back to mapping pane (Top)
            mapping_row_html = render_to_string('finance/partials/import_row.html', {
                't': transaction, 
                'categories': categories,
                'hx_oob': True
            })
            response_html += f'<div hx-swap-oob="afterbegin:#mapping-rows">{mapping_row_html}</div>'
            
            # Update the Total Sum in Ready Pane OOB
            total_ready = sum(t.amount for t in transaction.batch.transactions.filter(is_ignored=False, category__isnull=False))
            from django.contrib.humanize.templatetags.humanize import intcomma
            total_str = f"{intcomma(round(total_ready, 2))} EUR"
            response_html += f'<td id="total-ready-sum" hx-swap-oob="innerHTML">{total_str}</td>'
            
            return HttpResponse(response_html)
            
        # Standard case (staying in mapping or just updating field)
        return render(request, 'finance/partials/import_row.html', {'t': transaction, 'categories': categories})

    elif is_ready:
        # The row moved to "Ready" (Bottom). 
        # 1. Remove from mapping pane
        response_html = f'<tr id="mapping-row-{transaction.id}" hx-swap-oob="delete"></tr>'
        
        # 2. Add to ready pane
        ready_row_html = render_to_string('finance/partials/import_ready_row.html', {
            't': transaction, 
            'categories': categories,
            'hx_oob': True
        })
        response_html += ready_row_html
        
        # 3. Update the Total Sum OOB
        total_ready = sum(t.amount for t in transaction.batch.transactions.filter(is_ignored=False, category__isnull=False))
        from django.contrib.humanize.templatetags.humanize import intcomma
        total_str = f"{intcomma(round(total_ready, 2))} EUR"
        response_html += f'<td id="total-ready-sum" hx-swap-oob="innerHTML">{total_str}</td>'
        
        return HttpResponse(response_html)
    else:
        # It's ignored. Delete from whatever pane it was in.
        response_html = f'<tr id="mapping-row-{transaction.id}" hx-swap-oob="delete"></tr>'
        response_html += f'<tr id="ready-row-{transaction.id}" hx-swap-oob="delete"></tr>'
        
        # Update sum just in case it was in ready
        total_ready = sum(t.amount for t in transaction.batch.transactions.filter(is_ignored=False, category__isnull=False))
        from django.contrib.humanize.templatetags.humanize import intcomma
        total_str = f"{intcomma(round(total_ready, 2))} EUR"
        response_html += f'<td id="total-ready-sum" hx-swap-oob="innerHTML">{total_str}</td>'
        
        return HttpResponse(response_html)

@login_required
def apply_import_batch(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    if batch.is_applied:
        messages.warning(request, _("Dieser Import wurde bereits angewendet."))
        return redirect('dashboard')
        
    # Only import transactions that have a category assigned (Ready pane)
    transactions = batch.transactions.filter(is_ignored=False, category__isnull=False)
    total_unassigned = batch.transactions.filter(is_ignored=False, category__isnull=True).count()
    
    count_one_time = 0
    count_recurring = 0
    
    for t in transactions:
        import calendar
        last_day = calendar.monthrange(t.date.year, t.date.month)[1]
        
        CashFlowSource.objects.create(
            user=request.user,
            name=t.description,
            value=t.amount if t.is_income else abs(t.amount),
            is_income=t.is_income,
            start_date=t.date.replace(day=1),
            # Set to last day of the same month for historical data
            end_date=t.date.replace(day=last_day),
            category=t.category,
            frequency='monthly',
            is_inflation_adjusted=False,
            notes=t.matched_terms
        )
        count_recurring += 1
            
    # Cleanup: Delete the batch and its pending transactions now that they are applied
    # (We always delete the batch to avoid double-processing, even if some were skipped)
    batch.delete()
    
    msg = _(f"Import abgeschlossen: {count_recurring} Einträge erstellt.")
    if total_unassigned > 0:
        msg += " " + _(f"{total_unassigned} unzugeordnete Posten wurden verworfen.")
    
    messages.success(request, msg)
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
    log_content = latest_batch.ai_log if latest_batch else _eager("Warte auf Batch...")
    
    # Status and styling logic
    is_finished = (progress >= 100)
    is_error = (progress == -1)
    
    color_class = "bg-primary"
    if is_finished: color_class = "bg-success"
    if is_error: color_class = "bg-danger"
    
    progress_val = 100 if is_finished else (0 if is_error else progress)
    
    # Building the HTML fragment
    # IMPORTANT: We only include hx-get if NOT finished/error to STOP polling
    polling_attrs = ""
    if not (is_finished or is_error):
        polling_attrs = f'hx-get="/finance/import/progress/" hx-trigger="every 1.5s" hx-swap="outerHTML"'

    html = f'''
    <div id="progress-bar-placeholder" {polling_attrs}>
        <div class="progress shadow-sm" style="height: 25px; border-radius: 12px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated {color_class}" 
                 role="progressbar" 
                 style="width: {progress_val}%;" 
                 aria-valuenow="{progress_val}" 
                 aria-valuemin="0" 
                 aria-valuemax="100">
                 {progress_val}%
            </div>
        </div>
    '''
    
    if is_finished:
        review_url = reverse('review_transactions', args=[latest_batch.id])
        html += f'''
        <p class="text-center mt-2 text-success fw-bold">
            <i class="bi bi-check-circle-fill me-1"></i>{_eager("Analyse abgeschlossen!")}
        </p>
        <div class="mt-4 animate__animated animate__bounceIn">
            <a href="{review_url}" class="btn btn-success fw-bold shadow-lg px-5 py-3">
                <i class="bi bi-check-all me-2"></i>{_eager("Buchungen ansehen")}
            </a>
        </div>
        '''
    elif is_error:
        upload_url = reverse('import_transactions')
        error_msg = cache.get(f"import_error_{request.user.id}", _eager("Unbekannter Fehler"))
        html += f'''
        <p class="text-center mt-2 text-danger fw-bold">{_eager("Analyse fehlgeschlagen")}</p>
        <div class="alert alert-danger mt-3 small">
            <code>{error_msg}</code>
        </div>
        <div class="mt-3">
            <a href="{upload_url}" class="btn btn-outline-danger btn-sm px-4">
                <i class="bi bi-arrow-left me-2"></i>{_eager("Zurück zum Upload")}
            </a>
        </div>
        '''
    else:
        html += f'<p class="text-center mt-2 text-muted small fw-bold">{_eager("KI analysiert Daten...")} ({progress_val}%)</p>'

    # IMPORTANT: Close the placeholder div!
    html += f'''
        </div>
        <!-- Update the log window via OOB (Out of Band) swap -->
        <div id="ai-log-stream" hx-swap-oob="innerHTML">
            {log_content.replace("\n", "<br>")}
        </div>
    '''
    return HttpResponse(html)

@login_required
def import_search_as_group(request, batch_id):
    """
    Takes a search query and merges all matching (mapping) transactions 
    into a single 'Ready' transaction, while also learning the filter.
    """
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    q = request.POST.get('q', '').strip()
    target_name = request.POST.get('target_name', '').strip()
    category_id = request.POST.get('category_id')
    make_recurring = request.POST.get('make_recurring') == 'on'  # Checkbox value
    
    if not (q and target_name and category_id):
        return HttpResponse('<div class="alert alert-danger small">Bitte alle Felder ausfüllen.</div>', status=400)
    
    category = get_object_or_404(Category, id=category_id)
    
    # 1. Update/Create Filter
    filt, created = ImportFilter.objects.get_or_create(
        user=request.user,
        target_name=target_name,
        defaults={'category': category, 'search_query': q}
    )
    if not created:
        terms = [t.strip().upper() for t in filt.search_query.split(';') if t.strip()]
        if q.upper() not in terms:
            filt.search_query = f"{filt.search_query};{q}"
            filt.save()
            
    # --- Bridge to Finance Plan ---
    if make_recurring:
        # Create/Update CashFlowSource
        cf, cf_created = CashFlowSource.objects.get_or_create(
            user=request.user,
            name=target_name,
            defaults={
                'value': Decimal('0.00'),
                'category': category,
                'is_income': False
            }
        )
        # Update amount if new or zero
        if cf_created or cf.value == 0:
            # Re-sum the matches
            matches_for_sum = batch.transactions.filter(
                is_ignored=False, 
                category__isnull=True, 
                description__icontains=q
            )
            cf.value = abs(sum(m.amount for m in matches_for_sum))
            cf.save()
            
        filt.linked_cash_flow = cf
        filt.save()

    # 2. Find matching transactions (Mapping Only)
    matches = batch.transactions.filter(
        is_ignored=False, 
        category__isnull=True, 
        description__icontains=q
    )
    
    if not matches.exists():
        return HttpResponse('<div class="alert alert-warning small">Keine passenden Buchungen gefunden.</div>')

    # 3. Create or Update Consolidated Record (Ready Pane)
    from collections import defaultdict
    months_map = defaultdict(list)
    for m in matches:
        key = (m.date.year, m.date.month)
        months_map[key].append(m)
        
    response_html = ""
    for month_key, month_matches in months_map.items():
        total_amount = sum(m.amount for m in month_matches)
        total_count = sum(m.integration_count for m in month_matches)
        all_terms = "; ".join(set(m.description for m in month_matches))
        
        # Look for existing Ready record for this target/month
        ready_rec = batch.transactions.filter(
            description=target_name,
            date__year=month_key[0],
            date__month=month_key[1],
            category=category,
            is_ignored=False
        ).first()

        if ready_rec:
            ready_rec.amount += total_amount
            ready_rec.integration_count += total_count
            if ready_rec.matched_terms:
                ready_rec.matched_terms = f"{ready_rec.matched_terms}; {all_terms}"
            else:
                ready_rec.matched_terms = all_terms
            ready_rec.save()
            
            # Since it already exists, we UPDATE it OOB instead of appending
            response_html += render_to_string('finance/partials/import_ready_row.html', {
                't': ready_rec, 
                'categories': Category.objects.all(),
                'hx_oob': True
            }).replace(f'id="ready-row-{ready_rec.id}"', f'id="ready-row-{ready_rec.id}" hx-swap-oob="outerHTML:#ready-row-{ready_rec.id}"')
        else:
            ready_rec = PendingTransaction.objects.create(
                batch=batch,
                date=month_matches[0].date, # Representative date
                description=target_name,
                amount=total_amount,
                category=category,
                integration_count=total_count,
                matched_terms=all_terms,
                is_ignored=False
            )
            response_html += render_to_string('finance/partials/import_ready_row.html', {
                't': ready_rec, 
                'categories': Category.objects.all(),
                'hx_oob': True
            })
        
        # OOB Swaps to delete all matches from Mapping Pane
        for m in month_matches:
            response_html += f'<tr id="mapping-row-{m.id}" hx-swap-oob="delete"></tr>'
    
    # 3. Update the Total Sum OOB
    total_ready = sum(t.amount for t in batch.transactions.filter(is_ignored=False, category__isnull=False))
    from django.contrib.humanize.templatetags.humanize import intcomma
    total_str = f"{intcomma(round(total_ready, 2))} EUR"
    response_html += f'<td id="total-ready-sum" hx-swap-oob="innerHTML">{total_str}</td>'
    
    # 4. Remove empty state message if any
    response_html += '<tr id="empty-ready-msg" hx-swap-oob="delete"></tr>'

    return HttpResponse(response_html)

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

@login_required
def import_filters_list(request):
    filters = ImportFilter.objects.filter(user=request.user).order_by('target_name')
    categories = Category.objects.all()
    
    # Pre-fill values from GET if redirected from review
    pre_query = request.GET.get('pre_query', '')
    pre_name = request.GET.get('pre_name', '')
    batch_id = request.GET.get('batch_id', '')
    
    return render(request, 'finance/import_filters.html', {
        'filters': filters,
        'categories': categories,
        'pre_query': pre_query,
        'pre_name': pre_name,
        'batch_id': batch_id,
        'cash_flows': CashFlowSource.objects.filter(user=request.user).order_by('name')
    })

@login_required
def add_import_filter(request):
    if request.method == 'POST':
        query = request.POST.get('search_query')
        name = request.POST.get('target_name')
        cat_id = request.POST.get('category')
        batch_id = request.POST.get('batch_id')
        cf_id = request.POST.get('linked_cash_flow')
        
        category = Category.objects.filter(id=cat_id).first() if cat_id else None
        linked_cf = CashFlowSource.objects.filter(id=cf_id, user=request.user).first() if cf_id else None
        
        f = ImportFilter.objects.create(
            user=request.user,
            search_query=query,
            target_name=name,
            category=category,
            linked_cash_flow=linked_cf
        )
        messages.success(request, _("Filter erfolgreich hinzugefügt."))
        
        # HTMX support: Return the row and close modal
        if request.headers.get('HX-Request'):
            response = render(request, 'finance/partials/import_filter_row.html', {'f': f, 'hx_pob': True})
            response['HX-Trigger'] = 'filterAdded'
            return response

        # Smart Redirect fallback
        if batch_id:
            return redirect(f"{reverse('import_filters_list')}?batch_id={batch_id}")
            
    return redirect('import_filters_list')

@login_required
def edit_import_filter(request, filter_id):
    f = get_object_or_404(ImportFilter, id=filter_id, user=request.user)
    batch_id = request.POST.get('batch_id') or request.GET.get('batch_id')
    
    if request.method == 'POST':
        f.search_query = request.POST.get('search_query')
        f.target_name = request.POST.get('target_name')
        cat_id = request.POST.get('category')
        f.category = Category.objects.filter(id=cat_id).first() if cat_id else None
        cf_id = request.POST.get('linked_cash_flow')
        f.linked_cash_flow = CashFlowSource.objects.filter(id=cf_id, user=request.user).first() if cf_id else None
        f.save()
        messages.success(request, _("Filter erfolgreich geändert."))
        
        # HTMX support: Update row and close modal
        if request.headers.get('HX-Request'):
            response = render(request, 'finance/partials/import_filter_row.html', {'f': f, 'hx_pob': True})
            response['HX-Trigger'] = 'filterUpdated'
            return response

        if batch_id:
            return redirect(f"{reverse('import_filters_list')}?batch_id={batch_id}")
        return redirect('import_filters_list')

    return redirect('import_filters_list')

@login_required
def delete_import_filter(request, filter_id):
    f = get_object_or_404(ImportFilter, id=filter_id, user=request.user)
    batch_id = request.GET.get('batch_id')
    f.delete()
    messages.success(request, _("Filter gelöscht."))
    if batch_id:
        return redirect(f"{reverse('import_filters_list')}?batch_id={batch_id}")
    return redirect('import_filters_list')

@login_required
def quick_create_category(request):
    """
    HTMX view to create a category and return an OOB swap for all dropdowns.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '#6c757d')
        
        if not name:
            return HttpResponse('<div class="alert alert-danger small p-2">Name fehlt!</div>', status=400)
            
        category = Category.objects.create(name=name, color=color)
        
        # Build OOB response for ALL category dropdowns
        # 1. Update the original dropdown (regular response)
        # 2. Update OTHER dropdowns (OOB)
        # We'll return a special fragment that hx-swap-oob="beforeend:.category-select"
        
        new_option = f'<option value="{category.id}" selected>{category.name}</option>'
        
        html = f'''
            {new_option}
            <div hx-swap-oob="beforeend:.category-select">
                {new_option}
            </div>
            <div hx-swap-oob="innerHTML:#quick-cat-msg">
                <span class="text-success small"><i class="bi bi-check-circle"></i> Kategorie "{name}" erstellt!</span>
            </div>
        '''
        return HttpResponse(html)
    return HttpResponse(status=405)

@login_required
def quick_create_cash_flow(request):
    """
    HTMX view to quickly create a CashFlowSource and return it as an <option>.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        value = request.POST.get('value', '0').replace(',', '.')
        is_income = request.POST.get('is_income') == 'on'
        
        if not name:
            return HttpResponse('<div class="alert alert-danger small p-2">Name fehlt!</div>', status=400)
            
        try:
            val = Decimal(value)
        except:
            val = Decimal('0.00')

        cf = CashFlowSource.objects.create(
            user=request.user,
            name=name,
            value=val,
            is_income=is_income,
            frequency='monthly'
        )
        
        # Build OOB response for ALL CashFlow dropdowns
        new_option = f'<option value="{cf.id}" selected>{cf.name} ({cf.value} €)</option>'
        
        html = f'''
            {new_option}
            <div hx-swap-oob="beforeend:.cashflow-select">
                {new_option}
            </div>
            <div hx-swap-oob="innerHTML:#quick-cf-msg">
                <span class="text-success small"><i class="bi bi-check-circle"></i> Plan-Eintrag "{name}" erstellt!</span>
            </div>
        '''
        return HttpResponse(html)
    return HttpResponse(status=405)
