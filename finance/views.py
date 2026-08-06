from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.cache import cache
from django.utils.html import format_html
from django.utils.formats import number_format
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _, gettext as _eager
from django.contrib import messages
from .services import SimulationEngine
from .models import (
    Asset, CashFlowSource, OneTimeEvent, Pension, Category, 
    ImportBatch, PendingTransaction, ImportFilter, ProcessedTransactionHash
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
    'net_worth_chart': {
        'title': _('Net Worth Forecast'), 'type': 'line', 'default_width': 12, 'default_height': 'medium',
        'description': _('CHART_DESC_NET_WORTH')
    },
    'cashflow_chart': {
        'title': _('Cash Flow Analysis'), 'type': 'bar', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_CASH_FLOW')
    },
    'income_evolution_chart': {
        'title': _('Income & One-Time Effects'), 'type': 'bar', 'default_width': 12, 'default_height': 'medium',
        'description': _('CHART_DESC_INCOME_EVOLUTION')
    },
    'expense_evolution_chart': {
        'title': _('Expense Evolution'), 'type': 'line', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_EXPENSE_EVOLUTION')
    },
    'inflation_monitor_chart': {
        'title': _('Inflation Monitor'), 'type': 'line', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_INFLATION_MONITOR')
    },
    'budget_pie_chart': {
        'title': _('Monthly Budget'), 'type': 'pie', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_BUDGET_PIE')
    },
    'asset_allocation_chart': {
        'title': _('Asset Allocation'), 'type': 'doughnut', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_ASSET_ALLOCATION')
    },
    'upcoming_dates_widget': {
        'title': _('Important Dates & Deadlines'), 'type': 'table', 'default_width': 12, 'default_height': 'small',
        'description': _('WIDGET_DESC_UPCOMING_DATES')
    },
    'income_table_widget': {
        'title': _('Income Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small',
        'description': _('WIDGET_DESC_INCOME_TABLE')
    },

    'expense_table_widget': {
        'title': _('Expense Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small',
        'description': _('WIDGET_DESC_EXPENSE_TABLE')
    },
    'asset_table_widget': {
        'title': _('Asset Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small',
        'description': _('WIDGET_DESC_ASSET_TABLE')
    },
    'pension_table_widget': {
        'title': _('Pension Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small',
        'description': _('WIDGET_DESC_PENSION_TABLE')
    },
    'event_table_widget': {
        'title': _('One-Time Event Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small',
        'description': _('WIDGET_DESC_EVENT_TABLE')
    },
    'loan_table_widget': {
        'title': _('Loan Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small',
        'description': _('WIDGET_DESC_LOAN_TABLE')
    },
    'loan_evolution_chart': {
        'title': _('Loan Balance Trend'), 'type': 'line', 'default_width': 12, 'default_height': 'medium',
        'description': _('CHART_DESC_LOAN_EVOLUTION')
    },
    'real_estate_forecast_chart': {
        'title': _('Real Estate Trend'), 'type': 'line', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_REAL_ESTATE')
    },
    'physical_asset_forecast_chart': {
        'title': _('Physical Assets Trend'), 'type': 'line', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_PHYSICAL_ASSETS')
    },
    'liquid_pension_forecast_chart': {
        'title': _('Liquidity & Pension'), 'type': 'line', 'default_width': 6, 'default_height': 'small',
        'description': _('CHART_DESC_LIQUID_PENSION')
    },
}

SUMMARY_WIDGETS = {
    'current_assets': {
        'title': _('Current Assets'), 'default_bg': '#0d6efd', 'default_text': '#ffffff', 'icon': 'bi-wallet2',
        'description': _('SUMMARY_DESC_ASSETS')
    },
    'monthly_income': {
        'title': _('Monthly Income'), 'default_bg': '#198754', 'default_text': '#ffffff', 'icon': 'bi-graph-up-arrow',
        'description': _('SUMMARY_DESC_INCOME')
    },
    'monthly_expenses': {
        'title': _('Monthly Expenses'), 'default_bg': '#dc3545', 'default_text': '#ffffff', 'icon': 'bi-graph-down-arrow',
        'description': _('SUMMARY_DESC_EXPENSES')
    },
    'total_pensions': {
        'title': _('Pension Capital'), 'default_bg': '#0dcaf0', 'default_text': '#ffffff', 'icon': 'bi-bank',
        'description': _('SUMMARY_DESC_PENSION')
    },
    'expected_payout': {
        'title': _('Target Monthly Pension'), 'default_bg': '#6f42c1', 'default_text': '#ffffff', 'icon': 'bi-bullseye',
        'description': _('SUMMARY_DESC_TARGET_PENSION')
    },
    'current_pension_payout': {
        'title': _('Current Pension'), 'default_bg': '#fd7e14', 'default_text': '#ffffff', 'icon': 'bi-cash-stack',
        'description': _('SUMMARY_DESC_CURRENT_PENSION')
    },
    'total_physical_assets': {
        'title': _('Physical Assets'), 'default_bg': '#8a2be2', 'default_text': '#ffffff', 'icon': 'bi-car-front',
        'description': _('SUMMARY_DESC_PHYSICAL_ASSETS')
    },
    'total_real_estate': {
        'title': _('Real Estate'), 'default_bg': '#20c997', 'default_text': '#ffffff', 'icon': 'bi-house-heart',
        'description': _('SUMMARY_DESC_REAL_ESTATE')
    },
    'total_combined_assets': {
        'title': _('Total Wealth'), 'default_bg': '#ffc107', 'default_text': '#212529', 'icon': 'bi-pie-chart',
        'description': _('SUMMARY_DESC_TOTAL_WEALTH')
    },
    'total_debts': {
        'title': _('Total Debts'), 'default_bg': '#343a40', 'default_text': '#ffffff', 'icon': 'bi-credit-card-2-front',
        'description': _('SUMMARY_DESC_DEBTS')
    },
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
    Category.objects.get_or_create(slug='gesetzliche-rente', defaults={'name': _('State Pension'), 'color': '#0d6efd', 'is_system': True})
    Category.objects.get_or_create(slug='private-kapital-rente', defaults={'name': _('Private Pension'), 'color': '#0dcaf0', 'is_system': True})

    # Initialize or get Dashboard Config
    dashboard_config = profile.dashboard_config or {}

    # --- 0. Handle Configuration Updates FIRST (Post-Redirect-Get pattern or early update) ---
    if request.method == 'POST' and 'config_update' in request.POST:
        try:
            if request.POST.get('layout_json'):
                dashboard_config['layout'] = json.loads(request.POST.get('layout_json'))
            if request.POST.get('summary_layout_json'):
                dashboard_config['summary_layout'] = json.loads(request.POST.get('summary_layout_json'))
            if request.POST.get('simulation_panel_json'):
                dashboard_config['simulation_panel'] = json.loads(request.POST.get('simulation_panel_json'))
            
            profile.dashboard_config = dashboard_config
            profile.save()
            # We continue so the rest of the view uses the UPDATED dashboard_config
        except json.JSONDecodeError:
            pass
    
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

    # Ensure all available charts are in the layout (auto-add missing ones)
    existing_chart_ids = [item['id'] for item in layout]
    for chart_id, chart_info in AVAILABLE_CHARTS.items():
        if chart_id not in existing_chart_ids:
            layout.append({
                'id': chart_id,
                'visible': False,
                'width': chart_info.get('default_width', 6),
                'height': chart_info.get('default_height', 'small'),
                'order': len(layout) + 1
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
                'visible': True, 
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
    }
    
    simulation_params = profile_params.copy()
    current_today = timezone.now().date()
    simulation_params['stichtag'] = current_today

    # Session handling for persistent active simulation state
    if request.GET.get('reset_simulation'):
        if 'active_simulation' in request.session:
            del request.session['active_simulation']
        simulation_params = profile_params.copy()
        simulation_params['stichtag'] = current_today
    elif request.method == 'POST' and 'config_update' not in request.POST:
        # Handle Simulation Update from POST form
        def safe_float(val, default):
            try: return float(val) if val is not None and val != '' else default
            except (ValueError, TypeError): return default
                
        simulation_params['inflation_rate'] = safe_float(request.POST.get('inflation_rate'), profile_params['inflation_rate'])
        simulation_params['salary_increase'] = safe_float(request.POST.get('salary_increase'), profile_params['salary_increase'])
        simulation_params['pension_increase'] = safe_float(request.POST.get('pension_increase'), profile_params['pension_increase'])
        simulation_params['investment_return_offset'] = safe_float(request.POST.get('investment_return_offset'), profile_params['investment_return_offset'])
        simulation_params['real_estate_growth_rate'] = safe_float(request.POST.get('real_estate_growth_rate'), profile_params['real_estate_growth_rate'])
        
        stichtag_raw = request.POST.get('stichtag') or request.GET.get('stichtag')
        if stichtag_raw:
            try:
                simulation_params['stichtag'] = datetime.datetime.strptime(stichtag_raw, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                simulation_params['stichtag'] = current_today

        # Check if parameters actually differ from profile defaults
        param_diff = any(
            abs(float(simulation_params[k]) - float(profile_params[k])) > 0.001
            for k in profile_params
        )
        stichtag_diff = simulation_params['stichtag'].replace(day=1) != current_today.replace(day=1)
        
        if param_diff or stichtag_diff:
            sess_params = {k: float(v) for k, v in simulation_params.items() if k != 'stichtag'}
            sess_params['stichtag'] = simulation_params['stichtag'].strftime('%Y-%m-%d')
            request.session['active_simulation'] = sess_params
        else:
            if 'active_simulation' in request.session:
                del request.session['active_simulation']
    elif 'active_simulation' in request.session:
        # Restore active simulation parameters from session
        sess = request.session['active_simulation']
        for k in profile_params:
            if k in sess:
                simulation_params[k] = float(sess[k])
        if 'stichtag' in sess:
            try:
                simulation_params['stichtag'] = datetime.datetime.strptime(sess['stichtag'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                simulation_params['stichtag'] = current_today

    # Final check if active simulation differs from defaults
    param_diff = any(
        abs(float(simulation_params[k]) - float(profile_params[k])) > 0.001
        for k in profile_params
    )
    stichtag_diff = simulation_params['stichtag'].replace(day=1) != current_today.replace(day=1)
    is_simulation_active = param_diff or stichtag_diff

    # Charts affected by simulation parameters (future projections and forecast models)
    affected_charts = [
        'net_worth_chart',
        'cashflow_chart',
        'income_evolution_chart',
        'expense_evolution_chart',
        'inflation_monitor_chart',
        'real_estate_forecast_chart',
        'physical_asset_forecast_chart',
        'liquid_pension_forecast_chart',
        'loan_evolution_chart',
    ]

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
                'debug_breakdown': {},
            }
        
        bucket = yearly_buckets[year]
        # Net worth is a point-in-time value, take the last one of the year
        bucket['nominal_net_worth'] = d.get('nominal_net_worth', 0)
        bucket['real_net_worth'] = d.get('real_net_worth', 0)
        bucket['pension_total'] = d.get('pension_total', 0)
        bucket['real_pension_total'] = d.get('real_pension_total', 0)
        bucket['asset_total'] = d.get('asset_total', 0)
        bucket['real_asset_total'] = d.get('real_asset_total', 0)
        bucket['accumulated_cash'] = d.get('accumulated_cash', 0)
        bucket['real_accumulated_cash'] = d.get('real_accumulated_cash', 0)
        bucket['physical_asset_total'] = d.get('physical_asset_total', 0)
        bucket['physical_asset_real_total'] = d.get('real_physical_asset_total', 0)
        bucket['real_estate_total'] = d.get('real_estate_total', 0)
        bucket['real_estate_real_total'] = d.get('real_real_estate_total', 0)
        
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
            
        # Debug Breakdown (Detailed items)
        for cat, items in d.get('debug_breakdown', {}).items():
            if cat not in bucket['debug_breakdown']:
                bucket['debug_breakdown'][cat] = {}
            for item_name, val in items.items():
                bucket['debug_breakdown'][cat][item_name] = bucket['debug_breakdown'][cat].get(item_name, 0) + val
            
        # Loan Balances (Snapshot at end of year)
        if 'loan_balances' in d:
            bucket['loan_balances'] = d['loan_balances']

        # One Time Events
        if d['one_time_events']:
            bucket['one_time_events'].extend(d['one_time_events'])

    sorted_years = sorted(yearly_buckets.keys())
    
    labels_yearly = []
    net_worth_nominal = []
    net_worth_real = []
    pension_yearly = []
    pension_real_yearly = []
    liquid_assets_yearly = []
    liquid_assets_real_yearly = []
    physical_asset_yearly = []
    physical_asset_real_yearly = []
    real_estate_yearly = []
    real_estate_real_yearly = []
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
        pension_yearly.append(float(bucket['pension_total']))
        pension_real_yearly.append(float(bucket['real_pension_total']))
        
        # Combine base assets and accumulated cash for "Liquid Assets" line
        liquid_nominal = float(bucket['asset_total'] + bucket['accumulated_cash'])
        liquid_real = float(bucket['real_asset_total'] + bucket['real_accumulated_cash'])
        liquid_assets_yearly.append(liquid_nominal)
        liquid_assets_real_yearly.append(liquid_real)
        
        physical_asset_yearly.append(float(bucket['physical_asset_total']))
        physical_asset_real_yearly.append(float(bucket['physical_asset_real_total']))
        real_estate_yearly.append(float(bucket['real_estate_total']))
        real_estate_real_yearly.append(float(bucket['real_estate_real_total']))
        
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
    
    # Filter out income categories that are entirely zero
    income_evo_datasets = [ds for ds in income_evo_datasets if any(abs(v) > 0.1 for v in ds['data'])]
    
    # Add One-Time Effects dataset (if any exist and are non-zero)
    if any(abs(v) > 0.1 for v in one_time_yearly):
        income_evo_datasets.append({
            'label': _eager('One-Time Effects'),
            'data': one_time_yearly,
            'backgroundColor': '#ffecb3', # Light amber
            'borderColor': '#ffc107',     # Solid amber
            'borderWidth': 1,
            'stack': 'income',
            'tooltipData': one_time_tooltips
        })
    
    expense_evo_datasets = []
    for idx, cat in enumerate(sorted(list(expense_categories))):
        cat_data = [float(yearly_buckets[y]['category_breakdown'].get(cat, 0)) for y in sorted_years]
        # Collect debug breakdown for this specific category across years
        cat_debug = [yearly_buckets[y]['debug_breakdown'].get(cat, {}) for y in sorted_years]
        
        color = category_color_map.get(cat, fallback_colors[idx % len(fallback_colors)])
        expense_evo_datasets.append({
            'label': cat,
            'data': cat_data,
            'debugData': cat_debug,
            'backgroundColor': color,
            'borderColor': '#000000',
            'borderWidth': 1.5,
            'pointBackgroundColor': color,
            'pointBorderColor': '#000000',
            'fill': True
        })
    
    # Filter out expense categories that are entirely zero
    expense_evo_datasets = [ds for ds in expense_evo_datasets if any(abs(v) > 0.1 for v in ds['data'])]

    # 2.2 Loan Evolution Chart
    loan_evo_datasets = []
    user_loans_list = list(user.loans.all())
    loan_colors = ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#0d6efd', '#6610f2', '#6f42c1', '#e83e8c']
    
    for idx, l in enumerate(user_loans_list):
        l_id_str = str(l.id)
        l_data = []
        l_events_yearly = []
        
        for y in sorted_years:
            l_data.append(float(yearly_buckets[y]['loan_balances'].get(l_id_str, 0)))
            # Filter events for this specific loan
            y_events = [e for e in yearly_buckets[y]['one_time_events'] if e.get('loan_name') == l.name]
            l_events_yearly.append(y_events)
            
        # Only add if there is any debt in the simulation period
        if any(v > 0 for v in l_data):
            loan_evo_datasets.append({
                'label': l.name,
                'data': l_data,
                'borderColor': loan_colors[idx % len(loan_colors)],
                'backgroundColor': loan_colors[idx % len(loan_colors)] + '1A', # 10% alpha
                'fill': False,
                'borderWidth': 3,
                'tension': 0.1,
                'tooltipData': l_events_yearly
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

    def get_first_data_index(labels, all_chart_datasets):
        """
        Finds the earliest index across multiple chart datasets where data starts.
        """
        if not labels:
            return 0
        
        first_idx = len(labels)
        for datasets in all_chart_datasets:
            for ds in datasets:
                data = ds.get('data', [])
                for i, val in enumerate(data):
                    if val is not None and val != 0:
                        if i < first_idx:
                            first_idx = i
                        break
        
        if first_idx == len(labels):
            return 0
        return first_idx

    # DEBUG: Check debugData before trimming
    for ds in expense_evo_datasets:
        if 'debugData' in ds:
            print(f"DEBUG: Dataset {ds['label']} has debugData with length {len(ds['debugData'])}")

    def trim_chart_data(labels, datasets, stichtag_index=None, fixed_start_idx=None):
        """
        Trims leading zero-data periods using either a fixed index or auto-detection.
        """
        if not labels:
            return labels, datasets, stichtag_index

        if not datasets:
            idx = stichtag_index if stichtag_index is not None and 0 <= stichtag_index < len(labels) else 0
            return [labels[idx]], [], 0

        # If fixed_start_idx is provided, use it. Otherwise, auto-detect the first non-zero index.
        if fixed_start_idx is not None:
            first_idx = fixed_start_idx
        else:
            first_idx = len(labels)
            for ds in datasets:
                data = ds.get('data', [])
                for i, val in enumerate(data):
                    # Use a threshold to ignore rounding errors
                    if val is not None and abs(val) > 0.1:
                        if i < first_idx:
                            first_idx = i
                        break
        
        if first_idx >= len(labels):
            first_idx = 0
            
        # Trim labels and datasets
        trimmed_labels = labels[first_idx:]
        trimmed_datasets = []
        for ds in datasets:
            new_ds = ds.copy()
            # Automatically trim any list that has the same length as the original labels
            for key, value in ds.items():
                if isinstance(value, (list, tuple)) and len(value) == len(labels):
                    new_ds[key] = value[first_idx:]
                    # Write to a file since terminal logs are hard to see
                    with open('/tmp/debug_log.txt', 'a') as f:
                        f.write(f"DEBUG: Trimmed key '{key}' for dataset '{ds.get('label')}'. Length: {len(new_ds[key])}\n")
                        if key == 'debugData' and len(new_ds[key]) > 0:
                            f.write(f"  First item: {str(new_ds[key][0])[:100]}\n")
            trimmed_datasets.append(new_ds)
            
        # Adjust stichtag_index
        new_stichtag_index = stichtag_index
        if stichtag_index is not None:
            new_stichtag_index = max(0, stichtag_index - first_idx)
                
        return trimmed_labels, trimmed_datasets, new_stichtag_index

    # Force language activation for chart data to ensure consistent translation
    with translation.override(translation.get_language()):
        # 1. Trim each chart individually for maximum compactness (no leading zeros)
        nw_labels, nw_datasets, nw_stichtag = trim_chart_data(labels_yearly, [
            {'label': _('Net Worth (Nominal)'), 'data': net_worth_nominal, 'borderColor': '#0d6efd', 'fill': False, 'borderWidth': 4},
            {'label': _('Net Worth (Real)'), 'data': net_worth_real, 'borderColor': '#0d6efd', 'borderDash': [5, 5], 'fill': False, 'borderWidth': 2},
        ], stichtag_year_index)

        re_labels, re_datasets, re_stichtag = trim_chart_data(labels_yearly, [
            {'label': _('Real Estate (Nominal)'), 'data': real_estate_yearly, 'borderColor': '#fd7e14', 'backgroundColor': 'rgba(253, 126, 20, 0.1)', 'fill': True},
            {'label': _('Real Estate (Real)'), 'data': real_estate_real_yearly, 'borderColor': '#fd7e14', 'borderDash': [5, 5], 'fill': False},
        ], stichtag_year_index)

        pa_labels, pa_datasets, pa_stichtag = trim_chart_data(labels_yearly, [
            {'label': _('Physical Assets (Nominal)'), 'data': physical_asset_yearly, 'borderColor': '#8a2be2', 'backgroundColor': 'rgba(138, 43, 226, 0.1)', 'fill': True},
            {'label': _('Physical Assets (Real)'), 'data': physical_asset_real_yearly, 'borderColor': '#8a2be2', 'borderDash': [5, 5], 'fill': False},
        ], stichtag_year_index)

        lp_labels, lp_datasets, lp_stichtag = trim_chart_data(labels_yearly, [
            {'label': _('Liquid Assets (Nominal)'), 'data': liquid_assets_yearly, 'borderColor': '#198754', 'fill': False},
            {'label': _('Liquid Assets (Real)'), 'data': liquid_assets_real_yearly, 'borderColor': '#198754', 'borderDash': [5, 5], 'fill': False},
            {'label': _('Pension Capital (Nominal)'), 'data': pension_yearly, 'borderColor': '#6f42c1', 'fill': False},
            {'label': _('Pension Capital (Real)'), 'data': pension_real_yearly, 'borderColor': '#6f42c1', 'borderDash': [5, 5], 'fill': False},
        ], stichtag_year_index)

        # Cashflow Trend (Income vs Expenses)
        cf_labels, cf_datasets, cf_stichtag = trim_chart_data(labels_yearly, [
            {'label': _('Income'), 'data': income_yearly, 'backgroundColor': 'rgba(25, 135, 84, 0.7)', 'order': 2, 
             'debugData': [yearly_buckets[y]['income_category_breakdown'] for y in sorted_years]},
            {'label': _('Expenses'), 'data': expenses_yearly, 'backgroundColor': 'rgba(220, 53, 69, 0.7)', 'order': 2,
             'debugData': [yearly_buckets[y]['category_breakdown'] for y in sorted_years]},
            {'label': _('Net Savings'), 'data': net_savings_yearly, 'type': 'line', 'borderColor': '#0d6efd', 'borderWidth': 2, 'fill': False, 'pointRadius': 3, 'order': 1},
        ], stichtag_year_index)

        ie_labels, ie_datasets, ie_stichtag = trim_chart_data(labels_yearly, income_evo_datasets, stichtag_year_index)
        ee_labels, ee_datasets, ee_stichtag = trim_chart_data(labels_yearly, expense_evo_datasets, stichtag_year_index)
        le_labels, le_datasets, le_stichtag = trim_chart_data(labels_yearly, loan_evo_datasets, stichtag_year_index)

        im_labels, im_datasets, im_stichtag = trim_chart_data(labels_yearly, [
            {'label': _('Nominal Value'), 'data': net_worth_nominal, 'borderColor': '#0d6efd', 'fill': False},
            {'label': _('Real Value (Purchasing Power)'), 'data': net_worth_real, 'borderColor': '#198754', 'fill': False},
            {
                'label': _('Purchasing Power Loss'), 
                'data': inflation_loss, 
                'backgroundColor': 'rgba(220, 53, 69, 0.5)', 
                'type': 'bar',
                'percentData': inflation_loss_percent
            }
        ], stichtag_year_index)

        chart_datasets = {
            'net_worth_chart': {
                'labels': nw_labels,
                'datasets': nw_datasets,
                'stichtag_index': nw_stichtag
            },
            'real_estate_forecast_chart': {
                'labels': re_labels,
                'datasets': re_datasets,
                'stichtag_index': re_stichtag
            },
            'physical_asset_forecast_chart': {
                'labels': pa_labels,
                'datasets': pa_datasets,
                'stichtag_index': pa_stichtag
            },
            'liquid_pension_forecast_chart': {
                'labels': lp_labels,
                'datasets': lp_datasets,
                'stichtag_index': lp_stichtag
            },
            'cashflow_chart': {
                 'labels': cf_labels,
                 'datasets': cf_datasets,
                 'stichtag_index': cf_stichtag
            },
            'income_evolution_chart': {
                'labels': ie_labels,
                'datasets': ie_datasets,
                'stichtag_index': ie_stichtag
            },
            'expense_evolution_chart': {
                'labels': ee_labels,
                'datasets': ee_datasets,
                'stichtag_index': ee_stichtag
            },
            'budget_pie_chart': {
                'labels': budget_labels,
                'datasets': [{'data': budget_data, 'backgroundColor': budget_colors}]
            },
            'loan_evolution_chart': {
                'labels': le_labels,
                'datasets': le_datasets,
                'stichtag_index': le_stichtag
            },
            'inflation_monitor_chart': {
                'labels': im_labels,
                'datasets': im_datasets,
                'stichtag_index': im_stichtag
            },
            'asset_allocation_chart': {
                'labels': [
                    _('Liquid Assets'),
                    _('Pension Capital'),
                    _('Accumulated Cash'),
                    _('Physical Assets'),
                    _('Real Estate'),
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
            'upcoming_dates_widget': {
                'labels': [_eager('Date'), _eager('Categorisation'), _eager('Event'), _eager('Status')],
                'datasets': [] # We'll fill table_datasets instead
            }
        }

    # 6. Collect Important Dates/Deadlines
    upcoming_dates = []
    today = timezone.now().date()
    two_months_out = today + datetime.timedelta(days=60)
    
    # Loans
    for l in user.loans.all():
        if l.end_date and l.end_date >= today:
            upcoming_dates.append({
                'date': l.end_date, 'category': _('Loan'), 'name': f"{_('End of Loan')}: {l.name}",
                'status': 'urgent' if l.end_date <= two_months_out else 'info'
            })
        if l.interest_lock_end and l.interest_lock_end >= today:
            upcoming_dates.append({
                'date': l.interest_lock_end, 'category': _('Loan'), 'name': f"{_('End of Interest Lock')}: {l.name}",
                'status': 'warning' if l.interest_lock_end <= two_months_out else 'info'
            })
            
    # Pensions
    for p in user.pensions.all():
        if p.start_payout_date and p.start_payout_date >= today:
            upcoming_dates.append({
                'date': p.start_payout_date, 'category': _('Pension'), 'name': f"{_('Start of Payout')}: {p.provider}",
                'status': 'info'
            })
        if p.contribution_end_date and p.contribution_end_date >= today:
            upcoming_dates.append({
                'date': p.contribution_end_date, 'category': _('Pension'), 'name': f"{_('End of Contribution')}: {p.provider}",
                'status': 'info'
            })

    # Assets (Tagesgeld Hopping)
    for a in user.assets.all():
        if a.interest_teaser_until and a.interest_teaser_until >= today:
            upcoming_dates.append({
                'date': a.interest_teaser_until, 'category': _('Asset'), 'name': f"{_('Teaser Rate Expires')}: {a.name} ({a.interest_teaser_rate}%)",
                'status': 'danger' if a.interest_teaser_until <= today + datetime.timedelta(days=14) else ('warning' if a.interest_teaser_until <= two_months_out else 'info')
            })

    # Sales
    for pa in user.physical_assets.all():
        if pa.sale_date and pa.sale_date >= today:
            upcoming_dates.append({
                'date': pa.sale_date, 'category': _('Physical Asset'), 'name': f"{_('Planned Sale')}: {pa.name}",
                'status': 'info'
            })
            
    for re in user.real_estates.all():
        if re.sale_date and re.sale_date >= today:
            upcoming_dates.append({
                'date': re.sale_date, 'category': _('Real Estate'), 'name': f"{_('Planned Sale')}: {re.name}",
                'status': 'info'
            })

    # Cashflows
    for cf in user.cash_flows.filter(end_date__gte=today):
        upcoming_dates.append({
            'date': cf.end_date, 'category': _('Cash Flow'), 'name': f"{_('End of Cash Flow')}: {cf.name}",
            'status': 'warning' if cf.end_date <= two_months_out else 'info'
        })
        
    # Events
    for e in user.events.filter(date__gte=today):
        upcoming_dates.append({
            'date': e.date, 'category': _('Event'), 'name': e.name, 'status': 'info'
        })
        
    upcoming_dates.sort(key=lambda x: x['date'])
    # Only show next 10 or so
    upcoming_dates = upcoming_dates[:15]


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
    # Helper for formatting validity periods
    def format_period(start_dt, end_dt):
        if start_dt and end_dt:
            return f"{start_dt.strftime('%m/%Y')} - {end_dt.strftime('%m/%Y')}"
        elif start_dt:
            return f"ab {start_dt.strftime('%m/%Y')}"
        elif end_dt:
            return f"bis {end_dt.strftime('%m/%Y')}"
        return continuous_label

    table_data_income = []
    
    # 1. Manual Cash Flows (Income)
    for cf in user.cash_flows.select_related('category').filter(is_income=True):
        if (not cf.start_date or cf.start_date.replace(day=1) <= target_date) and \
           (not cf.end_date or cf.end_date.replace(day=1) >= target_date):
            amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
            table_data_income.append({
                'name': cf.name, 
                'amount': float(amt), 
                'category': cf.category.translated_name if cf.category else _('Income'),
                'type': _('Manual'),
                'year': format_period(cf.start_date, cf.end_date)
            })
    
    # 2. Asset withdrawals (Income, only if > 0)
    for a in user.assets.all():
        w_amt = float(a.withdrawal_amount or 0)
        if w_amt > 0 and a.withdrawal_start_date and a.withdrawal_start_date.replace(day=1) <= target_date:
            table_data_income.append({
                'name': f"{_('Withdrawal')}: {a.name}", 
                'amount': w_amt, 
                'category': _('Assets'),
                'type': _('Simulation'),
                'year': format_period(a.withdrawal_start_date, None)
            })

    # 3. Pension payouts (Income, only if > 0)
    for p in user.pensions.all():
        p_amt = float(p.expected_payout_at_retirement or 0)
        if p_amt > 0 and p.start_payout_date and p.start_payout_date.replace(day=1) <= target_date:
            table_data_income.append({
                'name': f"{_('Pension')}: {p.provider}", 
                'amount': p_amt, 
                'category': _('Pension'),
                'type': _('Contract'),
                'year': format_period(p.start_payout_date, None)
            })

    # 4. One-Time Income Events occurring at target_date month
    for e in user.events.all():
        if e.value and e.value > 0 and e.date and e.date.year == target_date.year and e.date.month == target_date.month:
            table_data_income.append({
                'name': f"{_('Event')}: {e.name}",
                'amount': float(e.value),
                'category': _('One-Time'),
                'type': _('Event'),
                'year': e.date.strftime('%d.%m.%Y')
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
                'category': cf.category.translated_name if cf.category else _('Expense'),
                'type': _('Manual'),
                'year': str(cf.start_date.year) if cf.start_date else continuous_label
            })

    # 2. Pension contributions (Expense)
    for p in user.pensions.all():
        if p.monthly_contribution and p.monthly_contribution > 0:
            if not p.contribution_end_date or p.contribution_end_date.replace(day=1) > target_date:
                table_data_expense.append({
                    'name': f"{_('Contribution')}: {p.provider}", 
                    'amount': float(p.monthly_contribution or 0), 
                    'category': _('Savings'),
                    'type': _('Contract'),
                    'year': str(p.contribution_end_date.year) if p.contribution_end_date else continuous_label
                })

    # 3. Loan installments (Expense)
    for l in user.loans.all():
        l_state = next((item for item in forecast_data if item['date'] == target_date), None)
        if (not l.end_date or l.end_date.replace(day=1) >= target_date) and (l.start_date.replace(day=1) <= target_date):
            table_data_expense.append({
                'name': f"{_('Loan Installment')}: {l.name}", 
                'amount': float(l.monthly_installment), 
                'category': _('Loan'),
                'type': _('Contract'),
                'year': str(l.end_date.year) if l.end_date else continuous_label
            })

    # 4. Physical Asset storage costs (Expense)
    for pa in user.physical_assets.all():
        if pa.storage_costs_monthly and pa.storage_costs_monthly > 0:
            is_owned = True
            if pa.acquisition_date and pa.acquisition_date.replace(day=1) > target_date:
                is_owned = False
            if pa.sale_date and pa.sale_date.replace(day=1) <= target_date:
                is_owned = False
            if pa.is_sold and target_date >= (pa.sale_date or today).replace(day=1):
                is_owned = False
            
            if is_owned:
                table_data_expense.append({
                    'name': f"{_('Storage')}: {pa.name}", 
                    'amount': float(pa.storage_costs_monthly), 
                    'category': _('Physical Assets'),
                    'type': _('Manual'),
                    'year': str(pa.sale_date.year) if pa.sale_date else continuous_label
                })

    # 5. Real Estate maintenance and ancillary costs (Expense)
    for re in user.real_estates.all():
        costs = (re.maintenance_costs_monthly or 0) + (re.ancillary_costs_monthly or 0)
        if costs > 0:
            is_owned = True
            if re.acquisition_date and re.acquisition_date.replace(day=1) > target_date:
                is_owned = False
            if re.sale_date and re.sale_date.replace(day=1) <= target_date:
                is_owned = False
            if re.is_sold and target_date >= (re.sale_date or today).replace(day=1):
                is_owned = False

            if is_owned:
                table_data_expense.append({
                    'name': f"{_('Maintenance/Costs')}: {re.name}", 
                    'amount': float(costs), 
                    'category': _('Real Estate'),
                    'type': _('Manual'),
                    'year': str(re.sale_date.year) if re.sale_date else continuous_label
                })

    table_data_asset = []
    for a in user.assets.all():
        rate_display = f"{a.growth_rate or 0}%"
        teaser_active = False
        if a.interest_teaser_rate is not None and a.interest_teaser_until and today <= a.interest_teaser_until:
            rate_display = f"{a.interest_teaser_rate}% -> {a.growth_rate or 0}%"
            teaser_active = True
            
        table_data_asset.append({
            'name': a.name, 
            'amount': float(a.value or 0), 
            'category': _('Asset'),
            'rate': rate_display,
            'year': continuous_label,
            'teaser_until': a.interest_teaser_until.strftime('%d.%m.%Y') if a.interest_teaser_until else None,
            'teaser_active': teaser_active
        })


    for p in user.pensions.all():
        table_data_asset.append({
            'name': f"{_('Pension')}: {p.provider}", 
            'amount': float(p.current_value or 0), 
            'category': _('Pension'),
            'rate': f"{p.growth_rate or 0}%",
            'year': continuous_label
        })

    table_data_pension = []
    for p in user.pensions.all():
        year = str(p.start_payout_date.year) if p.start_payout_date else continuous_label
        table_data_pension.append({
            'name': p.provider, 
            'amount': float(p.current_value or 0), 
            'category': _('Pension'),
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
            'type_display': str(l._meta.verbose_name),
            'amount': float(l.nominal_amount), 
            'current_balance': float(current_bal),
            'total_interest': float(total_int),
            'provider': l.provider,
            'interest_rate': float(l.interest_rate),
            'monthly_payment': float(l.monthly_installment),
            'year': str(l.end_date.year) if l.end_date else continuous_label
        })

    table_data_upcoming_dates = []
    for d in upcoming_dates:
        table_data_upcoming_dates.append({
            'date': d['date'].strftime('%d.%m.%Y'),
            'category': str(d['category']),
            'name': d['name'],
            'status': d['status']
        })

    table_datasets = {
        'income_table_widget': table_data_income,
        'expense_table_widget': table_data_expense,
        'asset_table_widget': table_data_asset,
        'pension_table_widget': table_data_pension,
        'event_table_widget': table_data_event,
        'loan_table_widget': table_data_loan,
        'upcoming_dates_widget': table_data_upcoming_dates,
    }
    table_json = {k: json.dumps(v, cls=DjangoJSONEncoder) for k, v in table_datasets.items()}


    # Key Metrics for Summary Panels

    # Ensure all chart titles and descriptions are eagerly translated in the current language context
    with translation.override(translation.get_language()):
        translated_available_charts = {
            k: {**v, 'title': _(str(v['title'])), 'description': _(str(v.get('description', '')))} 
            for k, v in AVAILABLE_CHARTS.items()
        }
        translated_summary_widgets = {
            k: {**v, 'title': _(str(v['title'])), 'description': _(str(v.get('description', '')))} 
            for k, v in SUMMARY_WIDGETS.items()
        }

        # --- Pre-attach titles and descriptions for easy template access ---
        for item in layout:
            info = translated_available_charts.get(item['id'], {})
            item['display_title'] = info.get('title', item['id'])
            item['help_text'] = info.get('description', '')
            
        for item in summary_layout:
            info = translated_summary_widgets.get(item['id'], {})
            item['display_title'] = info.get('title', item['id'])
            item['help_text'] = info.get('description', '')

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
        'affected_charts': affected_charts,
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
            # Only cleanup batches that are neither applied nor very recent
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

            return redirect('finance:import_processing')
    else:
        form = BankImportForm()
    
    ai_active = bool(settings.GEMINI_API_KEY) or bool(getattr(settings, 'GROQ_API_KEY', None))
    batches = ImportBatch.objects.filter(user=request.user).order_by('-date')
    
    return render(request, 'finance/import_upload.html', {
        'form': form,
        'ai_active': ai_active,
        'batches': batches
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

def _ensure_category_filters(user):
    """
    Robust synchronization: Ensures each category has exactly one ImportFilter.
    Prevents duplicates and re-links filters orphaned by category deletion.
    Atomic approach with IntegrityError handling to support multi-instance environments.
    """
    from django.db import IntegrityError
    all_categories = Category.objects.all()
    for cat in all_categories:
        # 1. Fast check: is it already correctly linked?
        if ImportFilter.objects.filter(user=user, category=cat).exists():
            continue
            
        # 2. Try to re-link an orphaned filter (category=NULL) with same name
        orphaned = ImportFilter.objects.filter(
            user=user, 
            category__isnull=True, 
            target_name=cat.name
        ).first()
        
        if orphaned:
            orphaned.category = cat
            orphaned.save()
        else:
            # 3. Double-check again right before creation to prevent race conditions
            if not ImportFilter.objects.filter(user=user, category=cat).exists():
                # 4. Create a fresh filter
                ImportFilter.objects.create(
                    user=user,
                    category=cat,
                    target_name=cat.name,
                    search_query='', # Field will be filled during review
                    is_active=True
                )

@login_required
def review_bank_transactions(request, batch_id):
    # Force resolution of the lazy request.user object to prevent 'CustomUser' object has no attribute 'user'
    user = request.user._wrapped if hasattr(request.user, '_wrapped') else request.user
    if not user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('login')
    
    profile = user.profile
    _ensure_category_filters(user)
    
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    
    # 1. Search Query for Mapping Pane
    q = request.GET.get('q', '').strip()
    
    # 2. Split into panes
    # Mapping: Not ignored, NO category
    mapping_qs = batch.transactions.select_related('category').filter(is_ignored=False, category__isnull=True)
    if q:
        mapping_qs = mapping_qs.filter(description__icontains=q)
    
    mapping_list = mapping_qs.order_by('date')
    
    # Ready: Not ignored, HAS category
    ready_list = batch.transactions.select_related('category', 'existing_source').filter(is_ignored=False, category__isnull=False).order_by('date', '-amount')
    
    # Total sum for Ready Pane
    total_ready = sum(t.amount for t in ready_list)
    
    categories = Category.objects.all()
    filters = ImportFilter.objects.filter(user=request.user).order_by('target_name')
    
    # Check if this is an HTMX request for specific panes
    if request.headers.get('HX-Request'):
        target = request.GET.get('target', '')
        if 'mapping-search' in target:
            return render(request, 'finance/partials/import_mapping_pane.html', {
                'transactions': mapping_list,
                'categories': categories,
                'batch': batch,
                'q': q,
                'profile': profile
            })
        elif 'ready-pane' in target:
            return render(request, 'finance/partials/import_ready_pane.html', {
                'ready_list': ready_list,
                'total_ready': total_ready,
                'profile': profile,
                'conflict_count': ready_list.filter(has_conflict=True, is_confirmed=False).count(),
                'batch': batch
            })

    return render(request, 'finance/import_review.html', {
        'batch': batch,
        'mapping_list': mapping_list,
        'ready_list': ready_list,
        'total_ready': total_ready,
        'categories': categories,
        'filters': filters,
        'q': q,
        'profile': profile,
        'ai_active': bool(settings.GEMINI_API_KEY or settings.GROQ_API_KEY),
        'conflict_count': ready_list.filter(has_conflict=True, is_confirmed=False).count()
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
    was_ready = (transaction.category is not None and not transaction.is_ignored)
    was_ignored = transaction.is_ignored
    
    if field == 'is_ignored':
        transaction.is_ignored = (value == 'true')
    elif field == 'is_recurring':
        transaction.is_recurring = (value == 'true')
    elif field == 'is_income':
        transaction.is_income = (value == 'true')
    elif field == 'category':
        from .llm import clean_description
        from .models import CategorizationMemory
        
        if value:
            cat = Category.objects.get(id=value)
            transaction.category = cat
            transaction.is_ready = True
            transaction.is_ignored = False
            
            # LEARNING: Save to categorization memory
            cleaned = clean_description(transaction.description)
            CategorizationMemory.objects.update_or_create(
                user=request.user, 
                description=cleaned,
                defaults={'category': cat}
            )
        else:
            transaction.category = None
            transaction.is_ready = False
            transaction.is_ignored = False
    elif field == 'frequency':
        transaction.frequency = value
    elif field == 'is_confirmed':
        transaction.is_confirmed = (value == 'true')
    transaction.save()
    
    is_mapping = (transaction.category is None and not transaction.is_ignored)
    is_ready = (transaction.category is not None and not transaction.is_ignored)
    is_ignored = transaction.is_ignored
    
    categories = Category.objects.all()
    batch = transaction.batch
    
    # Recalculate states for OOB updates
    mapping_count = batch.transactions.filter(is_ignored=False, category__isnull=True).count()
    ready_count = batch.transactions.filter(is_ignored=False, category__isnull=False).count()
    total_ready = sum(t.amount for t in batch.transactions.filter(is_ignored=False, category__isnull=False))
    
    from django.contrib.humanize.templatetags.humanize import intcomma
    total_str = f"{intcomma(round(total_ready, 2))}"
    
    # Build OOB Components
    oob_elements = []
    
    # 1. Total Sum update
    oob_elements.append(f'<span id="total-ready-sum" hx-swap-oob="innerHTML">{total_str}</span>')
    
    # 2. Empty Message Toggles
    if mapping_count == 0:
        # Show empty mapping message if not present
        empty_mapping_html = render_to_string('finance/partials/import_mapping_pane.html', {'transactions': [], 'batch': batch})
        # Extract only the empty message row part if possible, or just re-render the whole tbody
        oob_elements.append(f'<tbody id="mapping-rows" hx-swap-oob="innerHTML">{render_to_string("finance/partials/import_row_empty_msg.html") if "import_row_empty_msg.html" in locals() else "<tr><td colspan=\"6\" class=\"text-center py-5\"><h5 class=\"text-success\">Alle Posten zugeordnet!</h5></td></tr>"}</tbody>')
    elif was_mapping and mapping_count == 1:
        # If it was empty before (not really possible if we just moved one OUT, but if we moved one IN)
        pass 

    # 3. Handle Pane Transitions
    main_response = ""
    
    if was_mapping:
        if is_ready:
            # Move Mapping -> Ready
            main_response = "" # Deletes the row via hx-swap="delete" in template
            
            # OOB: Render ready row with built-in OOB logic
            oob_elements.append(render_to_string('finance/partials/import_ready_row.html', {
                't': transaction, 
                'categories': categories,
                'hx_oob': True
            }).strip())
            
            # OOB: Re-render total sum
            total_ready = sum(t.amount for t in PendingTransaction.objects.filter(batch=batch, is_ready=True, is_ignored=False))
            total_str = format_html('{}', number_format(total_ready, 2))
            oob_elements.append(f'<span id="total-ready-sum" hx-swap-oob="innerHTML">{total_str}</span>')

            # OOB: Empty Mapping Message
            if mapping_count == 0:
                msg = _("All items assigned!")
                oob_elements.append(f'<tr id="empty-mapping-msg" hx-swap-oob="afterbegin:#mapping-rows"><td colspan="6" class="text-center py-5 text-success fw-bold"><i class="bi bi-check-circle me-2"></i>{msg}</td></tr>')
            
            # OOB: Hide Empty Ready Message
            oob_elements.append('<tr id="empty-ready-msg" hx-swap-oob="delete"></tr>')
        elif is_ignored:
            # Move Mapping -> Ignored
            main_response = ""
        else:
            # Stay in Mapping (e.g. type toggle)
            main_response = render_to_string('finance/partials/import_row.html', {'t': transaction, 'categories': categories})
            
    elif was_ready:
        if is_mapping:
            # Move Ready -> Mapping
            main_response = "" # Deletes the row via hx-swap="delete" in template
            
            # OOB: Render mapping row with built-in OOB logic
            oob_elements.append(render_to_string('finance/partials/import_row.html', {
                't': transaction, 
                'categories': categories,
                'hx_oob': True
            }).strip())
            
            # OOB: Empty Ready Message
            if ready_count == 0:
                msg = _("No transactions ready yet.")
                oob_elements.append(f'<tr id="empty-ready-msg" hx-swap-oob="afterbegin:#ready-rows"><td colspan="7" class="text-center py-5 text-muted"><i class="bi bi-info-circle me-2"></i>{msg}</td></tr>')
            
            # OOB: Hide Empty Mapping Message
            oob_elements.append('<tr id="empty-mapping-msg" hx-swap-oob="delete"></tr>')
        elif is_ignored:
            # Move Ready -> Ignored
            main_response = ""
        else:
            # Stay in Ready (e.g. confirmation toggle)
            main_response = render_to_string('finance/partials/import_ready_row.html', {'t': transaction, 'categories': categories}).strip()

    # Final construction: No more manual OOB buildup, just trigger a global refresh
    response = HttpResponse(main_response)
    response['HX-Trigger'] = 'import-updated'
    return response

@login_required
def apply_import_batch(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    if batch.is_applied:
        messages.warning(request, _("This import has already been applied."))
        return redirect('finance:dashboard')
        
    # Only import transactions that have a category assigned (Ready pane)
    transactions = batch.transactions.filter(is_ignored=False, category__isnull=False)
    total_unassigned = batch.transactions.filter(is_ignored=False, category__isnull=True).count()
    
    # 1. Automatic Historical Alignment: 
    # For each category being imported, set end_date for previous years if still open.
    applied_categories = transactions.values_list('category', flat=True).distinct()
    import datetime
    
    for cat_id in applied_categories:
        # For each year in the current import
        import_years = transactions.filter(category_id=cat_id).values_list('date__year', flat=True).distinct()
        for yr in import_years:
            # Find the MOST RECENT entry for this category that was before this year and is still "open"
            old_entry = CashFlowSource.objects.filter(
                user=request.user,
                category_id=cat_id,
                start_date__year__lt=yr,
                end_date__isnull=True
            ).order_by('-start_date').first()
            
            if old_entry:
                # Set end_date to end of previous year
                old_entry.end_date = datetime.date(yr - 1, 12, 31)
                old_entry.save(update_fields=['end_date'])

    # 2. Process Transactions (NOW AGGREGATED per YEAR and CATEGORY)
    count_one_time = 0
    count_recurring = 0
    
    # We group rows by (Category, Year) to create or update yearly plan entries
    # The PendingTransactions already represent the years
    for t in transactions:
            # Check for same-year update (Conflict)
            if t.has_conflict:
                if not t.is_confirmed:
                    # Skip if conflict exists but user hasn't explicitly clicked "Overwrite"
                    continue
                
                # Overwrite existing source
                source = t.existing_source
                if source:
                    source.value = abs(t.amount)
                    source.name = t.description
                    source.is_income = t.is_income
                    source.notes = t.matched_terms
                    source.save()
                    count_recurring += 1
            else:
                # Create NEW yearly entry
                CashFlowSource.objects.create(
                    user=request.user,
                    name=t.description,
                    value=abs(t.amount),
                    is_income=t.is_income,
                    start_date=datetime.date(t.date.year, 1, 1),
                    category=t.category,
                    frequency='yearly',
                    is_inflation_adjusted=False,
                    notes=t.matched_terms
                )
                count_recurring += 1
            
    # 3. Persistent Memory: Remember which rows were handled (assigned or ignored)
    processed_transactions = batch.transactions.filter(
        models.Q(category__isnull=False) | models.Q(is_ignored=True)
    )
    for trans in processed_transactions:
        if trans.raw_signatures:
            sigs = [s for s in trans.raw_signatures.split(';') if s]
            hash_objs = [
                ProcessedTransactionHash(user=request.user, hash=sig, batch=batch)
                for sig in sigs
            ]
            ProcessedTransactionHash.objects.bulk_create(hash_objs, ignore_conflicts=True)

    # Mark as applied
    batch.is_applied = True
    batch.save(update_fields=['is_applied'])
    
    msg = _(f"Import successful: {count_recurring} plan entries created/updated.")
    if total_unassigned > 0:
        msg += " " + _(f"{total_unassigned} unassigned items were discarded.")
    
    messages.success(request, msg)
    return redirect('finance:dashboard')

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
    log_content = latest_batch.ai_log if latest_batch else _eager("Waiting for batch...")
    
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
        polling_attrs = f'hx-get="{reverse("finance:import_progress")}" hx-trigger="every 1.5s" hx-swap="outerHTML"'

    # We include a 'Cancel' button while the process is NOT finished or error.
    cancel_html = ""
    if not (is_finished or is_error) and latest_batch:
        cancel_url = reverse('finance:delete_import_batch', args=[latest_batch.id])
        cancel_html = f'''
        <div class="mt-3">
            <a href="{cancel_url}" 
               class="btn btn-outline-danger btn-sm px-4 w-100"
               onclick="return confirm('{_eager("Do you really want to cancel the analysis? All data from this import will be deleted.")}')">
                <i class="bi bi-x-circle me-1"></i> {_eager("Cancel analysis & Delete")}
            </a>
        </div>
        '''

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
        {cancel_html}
    '''
    
    if is_finished:
        review_url = reverse('finance:review_transactions', args=[latest_batch.id])
        html += f'''
        <p class="text-center mt-2 text-success fw-bold">
            <i class="bi bi-check-circle-fill me-1"></i>{_eager("Analysis complete!")}
        </p>
        <div class="mt-4 animate__animated animate__bounceIn">
             <a href="{review_url}" class="btn btn-success fw-bold shadow-lg px-5 py-3">
                <i class="bi bi-check-all me-2"></i>{_eager("View transactions")}
            </a>
        </div>
        '''
    elif is_error:
        upload_url = reverse('finance:import_transactions')
        error_msg = cache.get(f"import_error_{request.user.id}", _eager("Unbekannter Fehler"))
        html += f'''
        <p class="text-center mt-2 text-danger fw-bold">{_eager("Analysis failed")}</p>
        <div class="alert alert-danger mt-3 small">
            <code>{error_msg}</code>
        </div>
        <div class="mt-3">
            <a href="{upload_url}" class="btn btn-outline-danger btn-sm px-4">
                <i class="bi bi-arrow-left me-2"></i>{_eager("Back to upload")}
            </a>
        </div>
        '''
    else:
        html += f'<p class="text-center mt-2 text-muted small fw-bold">{_eager("AI is analyzing data...")} ({progress_val}%)</p>'

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
    filt = ImportFilter.objects.filter(user=request.user, target_name=target_name).first()
    created = False
    if not filt:
        filt = ImportFilter.objects.create(
            user=request.user,
            target_name=target_name,
            category=category,
            search_query=q
        )
        created = True
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
    # CRITICAL: We skip transactions that already have a category (manually assigned)
    matches = batch.transactions.filter(
        is_ignored=False, 
        category__isnull=True, 
        description__icontains=q
    )
    
    if not matches.exists():
        return HttpResponse('<div class="alert alert-warning small p-2 m-0 border-0">No further uncategorized transactions found.</div>')

    # 3. Create or Update Consolidated Record (Ready Pane)
    from collections import defaultdict
    months_map = defaultdict(list)
    for m in matches:
        key = (m.date.year, m.date.month)
        months_map[key].append(m)
        
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
        else:
            PendingTransaction.objects.create(
                batch=batch,
                date=month_matches[0].date, # Representative date
                description=target_name,
                amount=total_amount,
                is_income=(total_amount > 0),
                category=category,
                integration_count=total_count,
                matched_terms=all_terms,
                is_ignored=False
            )
            
    # 4. Mark originals as handled/hidden so they disappear from search results
    matches.update(is_ignored=True)
    
    # 5. Return success trigger. The front-end handles the actual re-render via HTMX events.
    response = HttpResponse("") 
    response['HX-Trigger'] = 'import-updated'
    return response

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
    
    messages.success(request, _(f"{count} temporary import records have been deleted."))
    return redirect('finance:import_transactions')

@login_required
def import_filters_list(request):
    filters = ImportFilter.objects.filter(user=request.user).select_related('category', 'linked_cash_flow').order_by('target_name')
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
        messages.success(request, _("Filter added successfully."))
        
        # HTMX support: Return the row and close modal
        if request.headers.get('HX-Request'):
            response = render(request, 'finance/partials/import_filter_row.html', {'f': f, 'hx_pob': True})
            response['HX-Trigger'] = 'filterAdded'
            return response

        # Smart Redirect fallback
        if batch_id:
            return redirect(f"{reverse('finance:import_filters_list')}?batch_id={batch_id}")
            
    return redirect('finance:import_filters_list')

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
        messages.success(request, _("Filter updated successfully."))
        
        # HTMX support: Update row and close modal
        if request.headers.get('HX-Request'):
            response = render(request, 'finance/partials/import_filter_row.html', {'f': f, 'hx_pob': True})
            response['HX-Trigger'] = 'filterUpdated'
            return response

        if batch_id:
            return redirect(f"{reverse('finance:import_filters_list')}?batch_id={batch_id}")
        return redirect('finance:import_filters_list')

    return redirect('finance:import_filters_list')

@login_required
def delete_import_filter(request, filter_id):
    f = get_object_or_404(ImportFilter, id=filter_id, user=request.user)
    batch_id = request.GET.get('batch_id')
    f.delete()
    messages.success(request, _("Filter deleted."))
    if batch_id:
        return redirect(f"{reverse('finance:import_filters_list')}?batch_id={batch_id}")
    return redirect('finance:import_filters_list')

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
            
        # 1. Prevent duplicate categories (case-insensitive check)
        category, created = Category.objects.get_or_create(
            name__iexact=name,
            defaults={'name': name, 'color': color}
        )
        
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

@login_required
def delete_import_batch(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    batch.delete()
    messages.success(request, _("Import batch deleted."))
    return redirect('finance:import_transactions')

@login_required
def delete_all_import_history(request):
    """
    Deletes ALL ImportBatch objects (and cascading PendingTransactions) 
    for the current user, including applied ones.
    """
    batches = ImportBatch.objects.filter(user=request.user)
    count = batches.count()
    batches.delete()
    
    # Also clear any stuck progress indicators in the cache
    cache_key = f"import_progress_{request.user.id}"
    cache.delete(cache_key)
    
    messages.success(request, _(f"Gesamte Import-Historie ({count} Batches) wurde gelöscht."))
    return redirect('finance:import_transactions')
def dynamic_theme_css(request):
    """
    Returns a dynamic CSS file based on the user's profile settings.
    This allows the browser to cache the CSS and prevents the middleware
    from having to inject large blocks of text into every HTML response.
    """
    try:
        if request.user.is_authenticated:
            profile = request.user.profile
            gs = profile.gradient_start or '#6610f2'
            ge = profile.gradient_end or '#0d6efd'
        else:
            gs = '#6610f2'
            ge = '#0d6efd'
    except Exception:
        gs = '#6610f2'
        ge = '#0d6efd'

    css_content = f"""
        @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css");

        .admin-interface #header {{
            background: linear-gradient(135deg, {gs} 0%, {ge} 100%) !important;
        }}
        /* Apply start color to the specific group of selectors provided by the user */
        .admin-interface .module h2, 
        .admin-interface .module caption, 
        .admin-interface .module.collapse details summary, 
        .admin-interface .module.filtered h2 {{
            background: {gs} !important;
            border-color: {gs} !important;
            color: #ffffff !important;
        }}
        #header h1 a, #header #user-tools, #header #user-tools a {{
            color: #ffffff !important;
        }}
        /* Apply start color to breadcrumbs */
        .breadcrumbs {{
            background: {gs} !important;
            color: #ffffff !important;
        }}
        .breadcrumbs a {{
            color: #ffffff !important;
            opacity: 0.9;
        }}
        .admin-interface .module.collapse details summary:hover {{
            opacity: 0.9 !important;
        }}
        /* Hide the logo on the fly */
        #header #branding img, 
        #header #branding svg,
        .admin-interface #header #branding img,
        .admin-interface #header #branding svg {{
            display: none !important;
        }}
        /* Ensure the branding text is white */
        #site-name a {{ color: white !important; }}

        /* Dashboard Link in Admin Header */
        .dashboard-link-admin {{
            color: rgba(255, 255, 255, 0.95) !important;
            text-transform: none !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", "Liberation Sans", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji" !important;
            text-decoration: none !important;
            border: none !important;
            display: inline-flex !important;
            align-items: center !important;
            margin-right: 15px !important;
            transition: all 0.2s ease !important;
            vertical-align: middle !important;
        }}
        .dashboard-link-admin:hover {{
            color: #ffffff !important;
            opacity: 1 !important;
            text-shadow: 0 0 10px rgba(255,255,255,0.3) !important;
            text-decoration: none !important;
        }}
        .dashboard-link-admin svg {{
            margin-right: 0.25rem !important; /* matches me-1 */
        }}

        /* Hide redundant admin header elements */
        #user-tools a[href="/"], 
        #user-tools a[href="/admin/"],
        .viewsite-link,
        #language-chooser,
        .language-chooser,
        form#language-chooser-form {{
            display: none !important;
        }}

        /* Tame the Django Admin Calendar size */
        .calendarbox {{
            font-size: 0.75rem !important;
            z-index: 1100 !important;
            width: auto !important;
        }}
        .calendarbox table {{
            margin: 0 !important;
            width: 100% !important;
        }}
        .calendarbox table th, .calendarbox table td {{
            padding: 2px !important;
            font-size: 0.7rem !important;
        }}
        .calendar-shortcuts {{
            font-size: 0.65rem !important;
            line-height: 1.2 !important;
            padding: 3px 0 !important;
        }}
        .calendar-caption {{
            font-size: 0.75rem !important;
            padding: 3px !important;
            font-weight: bold !important;
        }}
        .clockbox {{
            font-size: 0.75rem !important;
            z-index: 1100 !important;
        }}
    """
    return HttpResponse(css_content, content_type="text/css")


from .forms import CashFlowSourceForm
from django.db import transaction

@login_required
def cash_flow_list(request):
    user = request.user
    profile = user.profile
    today = timezone.now().date()
    current_year = today.year
    
    # 1. Fetch Manual Cash Flow Sources
    manual_cfs = list(user.cash_flows.select_related('category').order_by('-is_income', 'category__name', 'name'))
    categories = Category.objects.all().order_by('name')
    
    # 2. Build Unified Items List (Manual + Pensions + Real Estate + Assets + Physical Assets + Loans)
    unified_items = []
    
    # 2a. Manual Cash Flows
    for cf in manual_cfs:
        unified_items.append({
            'id': f"manual_{cf.id}",
            'raw_id': cf.id,
            'name': cf.name,
            'value': Decimal(str(cf.value)),
            'monthly_amount': Decimal(str(cf.monthly_amount)),
            'is_income': cf.is_income,
            'frequency': cf.frequency,
            'frequency_display': str(cf.get_frequency_display()),
            'category_id': cf.category.id if cf.category else None,
            'category_name': cf.category.name if cf.category else '',
            'category_translated': cf.category.translated_name if cf.category else '-',
            'start_date': cf.start_date,
            'end_date': cf.end_date,
            'is_inflation_adjusted': cf.is_inflation_adjusted,
            'notes': cf.notes or '',
            'source_type': 'manual',
            'source_label': str(_('Manuell')),
            'edit_url': '',
            'can_edit': True,
            'can_wizard': True,
        })
        
    # 2b. Pensions
    for p in user.pensions.all():
        if p.monthly_contribution and p.monthly_contribution > 0:
            unified_items.append({
                'id': f"pension_contrib_{p.id}",
                'raw_id': p.id,
                'name': f"{_('Sparbeitrag')}: {p.provider}",
                'value': Decimal(str(p.monthly_contribution)),
                'monthly_amount': Decimal(str(p.monthly_contribution)),
                'is_income': False,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Rente',
                'category_translated': str(_('Rente & Vorsorge')),
                'start_date': None,
                'end_date': p.contribution_end_date,
                'is_inflation_adjusted': p.is_indexed,
                'notes': f"{_('Modell Rente')}: {p.provider}",
                'source_type': 'pension',
                'source_label': str(_('Rente (Beitrag)')),
                'edit_url': f"/admin/finance/pension/{p.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })
        if p.expected_payout_at_retirement and p.expected_payout_at_retirement > 0:
            unified_items.append({
                'id': f"pension_payout_{p.id}",
                'raw_id': p.id,
                'name': f"{_('Rentenauszahlung')}: {p.provider}",
                'value': Decimal(str(p.expected_payout_at_retirement)),
                'monthly_amount': Decimal(str(p.expected_payout_at_retirement)),
                'is_income': True,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Rente',
                'category_translated': str(_('Rente & Vorsorge')),
                'start_date': p.start_payout_date,
                'end_date': None,
                'is_inflation_adjusted': p.is_indexed,
                'notes': f"{_('Modell Rente')}: {p.provider}",
                'source_type': 'pension',
                'source_label': str(_('Rente (Auszahlung)')),
                'edit_url': f"/admin/finance/pension/{p.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })

    # 2c. Real Estate
    for re in user.real_estates.all():
        if re.rental_income_monthly and re.rental_income_monthly > 0:
            unified_items.append({
                'id': f"re_income_{re.id}",
                'raw_id': re.id,
                'name': f"{_('Mieteinnahme')}: {re.name}",
                'value': Decimal(str(re.rental_income_monthly)),
                'monthly_amount': Decimal(str(re.rental_income_monthly)),
                'is_income': True,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Immobilien',
                'category_translated': str(_('Immobilien')),
                'start_date': re.acquisition_date,
                'end_date': re.sale_date,
                'is_inflation_adjusted': False,
                'notes': f"{_('Modell Immobilie')}: {re.name}",
                'source_type': 'real_estate',
                'source_label': str(_('Immobilie (Miete)')),
                'edit_url': f"/admin/finance/realestate/{re.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })
        if re.maintenance_costs_monthly and re.maintenance_costs_monthly > 0:
            unified_items.append({
                'id': f"re_expense_{re.id}",
                'raw_id': re.id,
                'name': f"{_('Instandhaltung')}: {re.name}",
                'value': Decimal(str(re.maintenance_costs_monthly)),
                'monthly_amount': Decimal(str(re.maintenance_costs_monthly)),
                'is_income': False,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Immobilien',
                'category_translated': str(_('Immobilien')),
                'start_date': re.acquisition_date,
                'end_date': re.sale_date,
                'is_inflation_adjusted': False,
                'notes': f"{_('Modell Immobilie')}: {re.name}",
                'source_type': 'real_estate',
                'source_label': str(_('Immobilie (Kosten)')),
                'edit_url': f"/admin/finance/realestate/{re.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })

    # 2d. Assets (Withdrawals)
    for a in user.assets.all():
        if a.withdrawal_amount and a.withdrawal_amount > 0:
            unified_items.append({
                'id': f"asset_withdrawal_{a.id}",
                'raw_id': a.id,
                'name': f"{_('Entnahme')}: {a.name}",
                'value': Decimal(str(a.withdrawal_amount)),
                'monthly_amount': Decimal(str(a.withdrawal_amount)),
                'is_income': True,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Vermögen',
                'category_translated': str(_('Vermögensentnahme')),
                'start_date': a.withdrawal_start_date,
                'end_date': None,
                'is_inflation_adjusted': False,
                'notes': f"{_('Modell Entnahme')}: {a.name}",
                'source_type': 'asset',
                'source_label': str(_('Entnahme')),
                'edit_url': f"/admin/finance/asset/{a.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })

    # 2e. Physical Assets
    for pa in user.physical_assets.all():
        if pa.storage_costs_monthly and pa.storage_costs_monthly > 0:
            unified_items.append({
                'id': f"pa_expense_{pa.id}",
                'raw_id': pa.id,
                'name': f"{_('Stellplatz/Lager')}: {pa.name}",
                'value': Decimal(str(pa.storage_costs_monthly)),
                'monthly_amount': Decimal(str(pa.storage_costs_monthly)),
                'is_income': False,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Sachwerte',
                'category_translated': str(_('Sachwerte')),
                'start_date': pa.acquisition_date,
                'end_date': pa.sale_date,
                'is_inflation_adjusted': False,
                'notes': f"{_('Modell Sachwert')}: {pa.name}",
                'source_type': 'physical_asset',
                'source_label': str(_('Sachwert (Kosten)')),
                'edit_url': f"/admin/finance/physicalasset/{pa.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })

    # 2f. Loans
    for loan in user.loans.all():
        if loan.monthly_installment and loan.monthly_installment > 0:
            unified_items.append({
                'id': f"loan_{loan.id}",
                'raw_id': loan.id,
                'name': f"{_('Kreditrate')}: {loan.name}",
                'value': Decimal(str(loan.monthly_installment)),
                'monthly_amount': Decimal(str(loan.monthly_installment)),
                'is_income': False,
                'frequency': 'monthly',
                'frequency_display': str(_('Monatlich')),
                'category_id': None,
                'category_name': 'Kredite',
                'category_translated': str(_('Kredite & Schulden')),
                'start_date': loan.start_date,
                'end_date': loan.end_date,
                'is_inflation_adjusted': False,
                'notes': f"{_('Modell Kredit')}: {loan.name}",
                'source_type': 'loan',
                'source_label': str(_('Kreditrate')),
                'edit_url': f"/admin/finance/loan/{loan.id}/change/",
                'can_edit': False,
                'can_wizard': False,
            })

    # 3. Determine available years
    years_set = {current_year - 2, current_year - 1, current_year, current_year + 1, current_year + 2}
    for item in unified_items:
        if item['start_date']:
            years_set.add(item['start_date'].year)
        if item['end_date']:
            years_set.add(item['end_date'].year)
    available_years = sorted(list(years_set), reverse=True)
    
    # Read year filter parameter (defaulting to current year)
    selected_year_str = request.GET.get('year', str(current_year))
    try:
        selected_year_val = int(selected_year_str)
    except (ValueError, TypeError):
        selected_year_val = 'all'
    
    monthly_income_sum = Decimal('0.00')
    monthly_expense_sum = Decimal('0.00')
    yearly_income_sum = Decimal('0.00')
    yearly_expense_sum = Decimal('0.00')
    
    for item in unified_items:
        if selected_year_val == 'all':
            is_active = True
            is_currently_running = not item['end_date'] or item['end_date'] >= today
        else:
            target_year = int(selected_year_val)
            year_start = datetime.date(target_year, 1, 1)
            year_end = datetime.date(target_year, 12, 31)
            
            # An item is active in target_year if its validity window overlaps target_year
            is_active = (not item['start_date'] or item['start_date'] <= year_end) and (not item['end_date'] or item['end_date'] >= year_start)
            # An item is currently running in target_year if it has not expired before target_year_end
            is_currently_running = is_active and (not item['end_date'] or item['end_date'] >= (today if target_year == current_year else year_end))
                
        item['is_active_in_selected_year'] = is_active
        item['is_expired_in_selected_year'] = not is_currently_running
        
        if is_active:
            m_val = item['monthly_amount']
            y_val = m_val * Decimal('12') if item['frequency'] == 'monthly' else item['value']
            
            # Only add to MONTHLY metric cards if the item is currently active (not expired)
            if is_currently_running:
                if item['is_income']:
                    monthly_income_sum += m_val
                else:
                    monthly_expense_sum += m_val
            
            # Add to YEARLY metric cards
            if item['is_income']:
                yearly_income_sum += y_val
            else:
                yearly_expense_sum += y_val
                
    monthly_income_sum = monthly_income_sum.quantize(Decimal('0.01'))
    monthly_expense_sum = monthly_expense_sum.quantize(Decimal('0.01'))
    monthly_net_surplus = (monthly_income_sum - monthly_expense_sum).quantize(Decimal('0.01'))
    yearly_income_sum = yearly_income_sum.quantize(Decimal('0.01'))
    yearly_expense_sum = yearly_expense_sum.quantize(Decimal('0.01'))
    yearly_net_surplus = (yearly_income_sum - yearly_expense_sum).quantize(Decimal('0.01'))
    
    filtered_items = [item for item in unified_items if item['is_active_in_selected_year']]
    
    items_json = []
    for item in filtered_items:
        s_date_str = item['start_date'].strftime('%Y-%m-%d') if item['start_date'] else ''
        e_date_str = item['end_date'].strftime('%Y-%m-%d') if item['end_date'] else ''
        
        if item['start_date'] and item['end_date']:
            period_fmt = f"{item['start_date'].strftime('%m/%Y')} - {item['end_date'].strftime('%m/%Y')}"
        elif item['start_date']:
            period_fmt = f"ab {item['start_date'].strftime('%m/%Y')}"
        elif item['end_date']:
            period_fmt = f"bis {item['end_date'].strftime('%m/%Y')}"
        else:
            period_fmt = str(_("Continuous"))

        items_json.append({
            'id': item['id'],
            'raw_id': item['raw_id'],
            'name': item['name'],
            'value': float(item['value']),
            'monthly_amount': float(item['monthly_amount']),
            'is_income': item['is_income'],
            'frequency': item['frequency'],
            'frequency_display': item['frequency_display'],
            'category_id': item['category_id'],
            'category_name': item['category_name'],
            'category_translated': item['category_translated'],
            'start_date': s_date_str,
            'end_date': e_date_str,
            'period_formatted': period_fmt,
            'is_inflation_adjusted': item['is_inflation_adjusted'],
            'notes': item['notes'],
            'source_type': item['source_type'],
            'source_label': item['source_label'],
            'edit_url': item['edit_url'],
            'can_edit': item['can_edit'],
            'can_wizard': item['can_wizard'],
            'is_expired': item['is_expired_in_selected_year']
        })

    # 4. Extract widget color settings from user's dashboard config
    dashboard_config = profile.dashboard_config or {}
    summary_layout = dashboard_config.get('summary_layout', [])
    summary_colors = {}
    for item in summary_layout:
        if isinstance(item, dict) and 'id' in item:
            summary_colors[item['id']] = {
                'bg_color': item.get('bg_color', ''),
                'text_color': item.get('text_color', '')
            }

    income_card_bg = summary_colors.get('monthly_income', {}).get('bg_color') or '#198754'
    income_card_text = summary_colors.get('monthly_income', {}).get('text_color') or '#ffffff'
    income_card_icon = SUMMARY_WIDGETS.get('monthly_income', {}).get('icon', 'bi-graph-up-arrow')

    expense_card_bg = summary_colors.get('monthly_expenses', {}).get('bg_color') or '#dc3545'
    expense_card_text = summary_colors.get('monthly_expenses', {}).get('text_color') or '#ffffff'
    expense_card_icon = SUMMARY_WIDGETS.get('monthly_expenses', {}).get('icon', 'bi-graph-down-arrow')

    surplus_card_icon = SUMMARY_WIDGETS.get('current_assets', {}).get('icon', 'bi-piggy-bank')

    context = {
        'cash_flows': manual_cfs,
        'cash_flows_json': json.dumps(items_json),
        'categories': categories,
        'available_years': available_years,
        'selected_year': selected_year_val,
        'current_year': current_year,
        'monthly_income_sum': monthly_income_sum,
        'monthly_expense_sum': monthly_expense_sum,
        'monthly_net_surplus': monthly_net_surplus,
        'yearly_income_sum': yearly_income_sum,
        'yearly_expense_sum': yearly_expense_sum,
        'yearly_net_surplus': yearly_net_surplus,
        'today': today,
        'form': CashFlowSourceForm(),
        'income_card_bg': income_card_bg,
        'income_card_text': income_card_text,
        'income_card_icon': income_card_icon,
        'expense_card_bg': expense_card_bg,
        'expense_card_text': expense_card_text,
        'expense_card_icon': expense_card_icon,
        'surplus_card_icon': surplus_card_icon,
    }
    return render(request, 'finance/cash_flow_list.html', context)


@login_required
def cash_flow_save(request, pk=None):
    user = request.user
    instance = get_object_or_404(CashFlowSource, id=pk, user=user) if pk else None
    
    if request.method == 'POST':
        form = CashFlowSourceForm(request.POST, instance=instance)
        if form.is_valid():
            cf = form.save(commit=False)
            cf.user = user
            cf.save()
            messages.success(request, _('Cash flow entry saved successfully.'))
        else:
            messages.error(request, _('Error saving entry. Please check your inputs.'))
    return redirect('finance:cash_flow_list')


@login_required
def cash_flow_delete(request, pk):
    user = request.user
    cf = get_object_or_404(CashFlowSource, id=pk, user=user)
    if request.method == 'POST':
        cf.delete()
        messages.success(request, _('Cash flow entry deleted.'))
    return redirect('finance:cash_flow_list')


@login_required
def cash_flow_annual_adjustment(request):
    if request.method == 'POST':
        user = request.user
        selected_ids = request.POST.getlist('selected_items')
        new_start_date_str = request.POST.get('new_start_date')
        adj_percent_str = request.POST.get('adjustment_percent', '0')
        
        if not selected_ids or not new_start_date_str:
            messages.error(request, _('Please select at least one entry and specify a valid new start date.'))
            return redirect('finance:cash_flow_list')
            
        try:
            new_start_date = datetime.datetime.strptime(new_start_date_str, '%Y-%m-%d').date()
            prev_end_date = new_start_date - datetime.timedelta(days=1)
            adj_percent = Decimal(str(adj_percent_str or '0'))
            multiplier = Decimal('1.0') + (adj_percent / Decimal('100'))
        except (ValueError, TypeError):
            messages.error(request, _('Invalid date or percentage value.'))
            return redirect('finance:cash_flow_list')
            
        sources = user.cash_flows.filter(id__in=selected_ids)
        copied_count = 0
        
        with transaction.atomic():
            for cf in sources:
                cf.end_date = prev_end_date
                cf.save()
                
                new_value = (cf.value * multiplier).quantize(Decimal('0.01'))
                note_suffix = f" [Anpassung ab {new_start_date.strftime('%d.%m.%Y')}]"
                new_notes = ((cf.notes or '') + note_suffix).strip()
                
                CashFlowSource.objects.create(
                    user=user,
                    name=cf.name,
                    value=new_value,
                    is_income=cf.is_income,
                    frequency=cf.frequency,
                    category=cf.category,
                    start_date=new_start_date,
                    end_date=None,
                    is_inflation_adjusted=cf.is_inflation_adjusted,
                    notes=new_notes
                )
                copied_count += 1
                
        messages.success(request, f"{_('Annual adjustment completed successfully.')} {copied_count} {_('entries updated and copied.')}")
    return redirect('finance:cash_flow_list')


from .forms import PensionForm

@login_required
def pension_plan_view(request):
    user = request.user
    profile = user.profile
    today = timezone.now().date()
    current_year = today.year

    pensions = list(user.pensions.all().order_by('pension_type', 'provider'))

    # Calculate retirement age & retirement year & simulation max year
    retirement_age = profile.retirement_age or 67
    sim_max_age = profile.simulation_max_age or 90
    birth_date = profile.birth_date
    if birth_date:
        retirement_year = birth_date.year + retirement_age
        sim_max_year = birth_date.year + sim_max_age
    else:
        retirement_year = current_year + (retirement_age - 40) # Default estimate
        sim_max_year = current_year + (sim_max_age - 40)

    # Fetch Snapshots for pensions
    from django.contrib.contenttypes.models import ContentType
    from .models import AssetSnapshot
    ct_pension = ContentType.objects.get_for_model(Pension)

    pension_ids = [p.id for p in pensions]
    snapshots = list(AssetSnapshot.objects.filter(
        user=user,
        content_type=ct_pension,
        object_id__in=pension_ids
    ).order_by('date'))

    # Metrics
    total_statutory_points = Decimal('0.0000')
    statutory_monthly_net = Decimal('0.00')
    private_monthly_net = Decimal('0.00')
    total_monthly_net = Decimal('0.00')
    total_capital_value = Decimal('0.00')

    for p in pensions:
        if p.pension_type == 'statutory':
            if p.pension_points:
                total_statutory_points += p.pension_points
            if p.expected_payout_at_retirement:
                statutory_monthly_net += p.expected_payout_at_retirement
        else:
            if p.expected_payout_at_retirement:
                private_monthly_net += p.expected_payout_at_retirement
            if p.current_value:
                total_capital_value += p.current_value

        if p.expected_payout_at_retirement:
            total_monthly_net += p.expected_payout_at_retirement

    target_monthly_payout = profile.expected_payout if hasattr(profile, 'expected_payout') and profile.expected_payout else total_monthly_net
    pension_gap = (target_monthly_payout - total_monthly_net).quantize(Decimal('0.01')) if target_monthly_payout else Decimal('0.00')

    # Build historical & forecast timeline up to simulation_max_year
    earliest_snap_year = min([s.date.year for s in snapshots]) if snapshots else current_year - 5
    start_year = min(earliest_snap_year, current_year - 3)
    end_year = max(sim_max_year, current_year + 5)
    timeline_years = list(range(start_year, end_year + 1))

    # Group snapshots by year
    snapshots_by_year = {}
    for s in snapshots:
        y = s.date.year
        if y not in snapshots_by_year:
            snapshots_by_year[y] = {'points': Decimal('0.00'), 'statutory_net': Decimal('0.00'), 'val': Decimal('0.00')}
        if s.pension_points:
            snapshots_by_year[y]['points'] += s.pension_points
            # Net pension calculation for statutory points in snapshot: points * point_value minus social deduction (~11.5%)
            pt_val = s.point_value or Decimal('39.32')
            gross = s.pension_points * pt_val
            net = gross * Decimal('0.885')  # ~11.5% deduction
            snapshots_by_year[y]['statutory_net'] += net
        if s.value:
            snapshots_by_year[y]['val'] += s.value

    # Build chart data series
    chart_years = []
    capital_series = []
    statutory_net_history_series = []
    net_payout_series = []
    target_series = []

    pension_increase_rate = profile.pension_increase / Decimal('100.0')

    for y in timeline_years:
        chart_years.append(str(y))
        target_series.append(float(target_monthly_payout))

        # 1. Historical Snapshots (years < current_year)
        y_snap = snapshots_by_year.get(y)
        if y < current_year:
            cap = float(y_snap['val']) if y_snap and y_snap['val'] > 0 else None
            stat_net = float(y_snap['statutory_net']) if y_snap and y_snap['statutory_net'] > 0 else None
            net_payout_series.append(0.0)
        else: # y >= current_year
            # Statutory Net Pension Projection (increases with pension_increase_rate into future)
            if y == current_year:
                stat_net_val = statutory_monthly_net
            else:
                years_ahead = y - current_year
                stat_net_val = statutory_monthly_net * ((Decimal('1.0') + pension_increase_rate) ** Decimal(str(years_ahead)))
            stat_net = float(stat_net_val.quantize(Decimal('0.01')))

            # Private Capital Projection (accumulates contributions, remains constant until payout start, then depletes by annual payout)
            if y == current_year:
                cap_val = total_capital_value
            else:
                # Calculate capital for year y based on previous year capital
                prev_cap_val = capital_series[-1] if (capital_series and capital_series[-1] is not None) else None
                prev_cap = Decimal(str(prev_cap_val)) if prev_cap_val is not None else total_capital_value
                annual_contrib = sum([(p.monthly_contribution or Decimal('0.00')) * Decimal('12.0') for p in pensions if p.pension_type != 'statutory' and (not p.contribution_end_date or p.contribution_end_date.year >= y)])
                annual_payout = sum([(p.expected_payout_at_retirement or Decimal('0.00')) * Decimal('12.0') for p in pensions if p.pension_type != 'statutory' and (p.start_payout_date and p.start_payout_date.year <= y)])
                cap_val = max(Decimal('0.00'), prev_cap + annual_contrib - annual_payout)
            cap = float(cap_val.quantize(Decimal('0.01')))

            # Monthly Net Payout Timeline
            yearly_projected_net = Decimal('0.00')
            for p in pensions:
                p_start_year = p.start_payout_date.year if p.start_payout_date else retirement_year
                if y >= p_start_year and p.expected_payout_at_retirement:
                    years_in_payout = y - p_start_year
                    if p.is_indexed:
                        p_payout = p.expected_payout_at_retirement * ((Decimal('1.0') + pension_increase_rate) ** Decimal(str(years_in_payout)))
                    else:
                        p_payout = p.expected_payout_at_retirement
                    yearly_projected_net += p_payout

            if yearly_projected_net == Decimal('0.00') and total_monthly_net > Decimal('0.00'):
                yearly_projected_net = total_monthly_net

            net_payout_series.append(float(yearly_projected_net.quantize(Decimal('0.01'))))

        capital_series.append(cap)
        statutory_net_history_series.append(stat_net)

    # Dashboard colors
    dashboard_config = profile.dashboard_config or {}
    summary_layout = dashboard_config.get('summary_layout', [])
    summary_colors = {item['id']: item for item in summary_layout if isinstance(item, dict) and 'id' in item}

    statutory_color = summary_colors.get('current_pension_payout', {}).get('bg_color') or '#fd7e14'
    private_color = summary_colors.get('total_pensions', {}).get('bg_color') or '#0dcaf0'
    target_color = summary_colors.get('expected_payout', {}).get('bg_color') or '#6f42c1'

    pensions_json = []
    for p in pensions:
        pensions_json.append({
            'id': p.id,
            'provider': p.provider,
            'pension_type': p.pension_type,
            'pension_type_display': str(p.get_pension_type_display()),
            'pension_points': float(p.pension_points) if p.pension_points is not None else None,
            'point_value': float(p.point_value) if p.point_value is not None else None,
            'gross_payout_amount': float(p.gross_payout_amount) if p.gross_payout_amount is not None else None,
            'social_deduction_rate': float(p.social_deduction_rate) if p.social_deduction_rate is not None else 11.5,
            'expected_payout_at_retirement': float(p.expected_payout_at_retirement) if p.expected_payout_at_retirement is not None else None,
            'current_value': float(p.current_value) if p.current_value is not None else 0.0,
            'monthly_contribution': float(p.monthly_contribution) if p.monthly_contribution is not None else 0.0,
            'start_payout_date': p.start_payout_date.strftime('%Y-%m-%d') if p.start_payout_date else '',
            'contribution_end_date': p.contribution_end_date.strftime('%Y-%m-%d') if p.contribution_end_date else '',
            'is_indexed': p.is_indexed,
            'notes': p.notes or ''
        })

    context = {
        'pensions': pensions,
        'pensions_json': json.dumps(pensions_json),
        'total_statutory_points': total_statutory_points,
        'statutory_monthly_net': statutory_monthly_net,
        'private_monthly_net': private_monthly_net,
        'total_monthly_net': total_monthly_net,
        'total_capital_value': total_capital_value,
        'target_monthly_payout': target_monthly_payout,
        'pension_gap': pension_gap,
        'pension_gap_abs': abs(pension_gap),
        'retirement_age': retirement_age,
        'retirement_year': retirement_year,
        'chart_years_json': json.dumps(chart_years),
        'capital_series_json': json.dumps(capital_series),
        'statutory_net_history_series_json': json.dumps(statutory_net_history_series),
        'net_payout_series_json': json.dumps(net_payout_series),
        'target_series_json': json.dumps(target_series),
        'statutory_color': statutory_color,
        'private_color': private_color,
        'target_color': target_color,
        'form': PensionForm(),
    }
    return render(request, 'finance/pension_plan.html', context)


@login_required
def pension_save(request, pk=None):
    user = request.user
    instance = get_object_or_404(Pension, id=pk, user=user) if pk else None

    if request.method == 'POST':
        form = PensionForm(request.POST, instance=instance)
        if form.is_valid():
            pension = form.save(commit=False)
            pension.user = user
            pension.save()
            messages.success(request, _('Pension entry saved successfully.'))
        else:
            messages.error(request, _('Error saving pension entry. Please check your inputs.'))
    return redirect('finance:pension_plan')


@login_required
def pension_delete(request, pk):
    user = request.user
    pension = get_object_or_404(Pension, id=pk, user=user)
    if request.method == 'POST':
        pension.delete()
        messages.success(request, _('Pension entry deleted.'))
    return redirect('finance:pension_plan')


@login_required
def pension_snapshot_save(request):
    if request.method == 'POST':
        user = request.user
        pension_id = request.POST.get('pension_id')
        snapshot_date_str = request.POST.get('date')
        points_str = request.POST.get('pension_points')
        point_val_str = request.POST.get('point_value')
        value_str = request.POST.get('value')
        notes = request.POST.get('notes', '')

        pension = get_object_or_404(Pension, id=pension_id, user=user)
        from django.contrib.contenttypes.models import ContentType
        from .models import AssetSnapshot

        try:
            snap_date = datetime.datetime.strptime(snapshot_date_str, '%Y-%m-%d').date()
            pts = Decimal(points_str) if points_str else None
            pt_val = Decimal(point_val_str) if point_val_str else None
            val = Decimal(value_str) if value_str else (pts * pt_val if pts and pt_val else Decimal('0.00'))

            AssetSnapshot.objects.update_or_create(
                user=user,
                content_type=ContentType.objects.get_for_model(Pension),
                object_id=pension.id,
                date=snap_date,
                defaults={
                    'value': val,
                    'pension_points': pts,
                    'point_value': pt_val,
                    'notes': notes
                }
            )
            messages.success(request, _('Historical snapshot saved successfully.'))
        except Exception as e:
            messages.error(request, f"{_('Error saving snapshot')}: {str(e)}")

    return redirect('finance:pension_plan')
