from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from .services import SimulationEngine
from django.core.serializers.json import DjangoJSONEncoder
import json
from decimal import Decimal

# Define available charts and their default properties
AVAILABLE_CHARTS = {
    'net_worth_chart': {'title': _('Net Worth Forecast'), 'type': 'line', 'default_width': 12, 'default_height': 'medium'},
    'cashflow_chart': {'title': _('Cash Flow Analysis'), 'type': 'bar', 'default_width': 6, 'default_height': 'small'},
    'income_evolution_chart': {'title': _('Income & One-Time Effects'), 'type': 'bar', 'default_width': 12, 'default_height': 'medium'},
    'expense_evolution_chart': {'title': _('Expense Evolution'), 'type': 'line', 'default_width': 6, 'default_height': 'small'},
    'inflation_monitor_chart': {'title': _('Inflation Monitor'), 'type': 'line', 'default_width': 6, 'default_height': 'small'},
    'budget_pie_chart': {'title': _('Monthly Budget'), 'type': 'pie', 'default_width': 6, 'default_height': 'small'},
    'income_table_widget': {'title': _('Income Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'expense_table_widget': {'title': _('Expense Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'asset_table_widget': {'title': _('Asset Withdrawal Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'pension_table_widget': {'title': _('Pension Contribution Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'event_table_widget': {'title': _('One-Time Event Table (Prorated)'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
}

SUMMARY_WIDGETS = {
    'current_assets': {'title': _('Current Assets'), 'default_bg': '#0d6efd', 'default_text': '#ffffff'},
    'monthly_income': {'title': _('Monthly Income'), 'default_bg': '#198754', 'default_text': '#ffffff'},
    'monthly_expenses': {'title': _('Monthly Expenses'), 'default_bg': '#dc3545', 'default_text': '#ffffff'},
    'total_pensions': {'title': _('Total Pensions'), 'default_bg': '#0dcaf0', 'default_text': '#ffffff'},
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
    profile = user.profile
    
    # Initialize or get Dashboard Config
    dashboard_config = profile.dashboard_config or {}
    layout = dashboard_config.get('layout', DEFAULT_LAYOUT)
    summary_layout = dashboard_config.get('summary_layout', [
        {'id': 'current_assets', 'visible': True, 'bg_color': '#0d6efd', 'text_color': '#ffffff', 'order': 1},
        {'id': 'monthly_income', 'visible': True, 'bg_color': '#198754', 'text_color': '#ffffff', 'order': 2},
        {'id': 'monthly_expenses', 'visible': True, 'bg_color': '#dc3545', 'text_color': '#ffffff', 'order': 3},
        {'id': 'total_pensions', 'visible': True, 'bg_color': '#0dcaf0', 'text_color': '#ffffff', 'order': 4},
    ])
    
    simulation_config = dashboard_config.get('simulation_panel', {
        'bg_color': '#ffffff', 
        'text_color': '#212529',
        'header_bg_color': '#ffc107',
        'header_text_color': '#212529'
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

    # Simulation Params from Profile
    profile_params = {
        'inflation_rate': float(profile.inflation_rate),
        'salary_increase': float(profile.salary_increase),
        'investment_return_offset': float(profile.investment_return_offset),
    }
    
    # Use profile_params as baseline, then potentially override with POST data
    simulation_params = profile_params.copy()

    if request.method == 'POST':
        if 'config_update' in request.POST:
            # Handle Configuration Update
            try:
                layout_json = request.POST.get('layout_json')
                summary_layout_json = request.POST.get('summary_layout_json')
                if layout_json:
                    new_layout = json.loads(layout_json)
                    dashboard_config['layout'] = new_layout
                if summary_layout_json:
                    new_summary_layout = json.loads(summary_layout_json)
                    dashboard_config['summary_layout'] = new_summary_layout
                
                simulation_panel_json = request.POST.get('simulation_panel_json')
                if simulation_panel_json:
                    new_sim_config = json.loads(simulation_panel_json)
                    dashboard_config['simulation_panel'] = new_sim_config
                
                profile.dashboard_config = dashboard_config
                profile.save()
                return redirect('dashboard')
            except json.JSONDecodeError:
                pass # Handle error
        else:
            # Handle Simulation Update (Temporary for this view/request)
            def safe_float(val, default):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default
                    
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
    # 1. Net Worth & General Labels
    labels_yearly = []
    net_worth_nominal = []
    net_worth_real = []
    
    birth_date = profile.birth_date
    
    for d in forecast_data[::12]:
        year = d['date'].year
        label = str(year)
        if birth_date:
            age = year - birth_date.year - ((d['date'].month, d['date'].day) < (birth_date.month, birth_date.day))
            label = f"{year} ({age})"
        labels_yearly.append(label)
        net_worth_nominal.append(float(d['nominal_net_worth']))
        net_worth_real.append(float(d['real_net_worth']))

    # 2. Cashflow (Aggregated by year) + Net Savings
    income_yearly = [float(d['monthly_income']) * 12 for d in forecast_data[::12]]
    expenses_yearly = [-float(d['monthly_expenses']) * 12 for d in forecast_data[::12]]
    net_savings_yearly = [inc + exp for inc, exp in zip(income_yearly, expenses_yearly)]

    # 3. Budget Pie (Current/Start month breakdown)
    if forecast_data:
        first_month = forecast_data[0]
        budget_labels = list(first_month['category_breakdown'].keys())
        budget_data = list(first_month['category_breakdown'].values())
    else:
        first_month = {}
        budget_labels = []
        budget_data = []

    # 4. Expense Evolution (Stacked categories over years)
    categories = set()
    for d in forecast_data[::12]:
        categories.update(d['category_breakdown'].keys())
    
    expense_evo_datasets = []
    for cat in sorted(list(categories)):
        cat_data = [float(d['category_breakdown'].get(cat, 0)) * 12 for d in forecast_data[::12]]
        expense_evo_datasets.append({
            'label': cat,
            'data': cat_data,
            'fill': True
        })

    # 5. Inflation Monitor (Real vs Nominal Gap + Lines)
    inflation_loss = []
    inflation_loss_percent = []
    for d in forecast_data[::12]:
        nom = float(d['nominal_net_worth'])
        real = float(d['real_net_worth'])
        loss = nom - real
        inflation_loss.append(loss)
        if nom > 0:
            percent = (loss / nom) * 100
        else:
            percent = 0.0
        inflation_loss_percent.append(percent)

    inflation_data = {
        'labels': labels_yearly,
        'nominal': net_worth_nominal,
        'real': net_worth_real,
        'loss': inflation_loss,
        'loss_percent': inflation_loss_percent
    }

    # 6. Income Evolution + One-Time Events (NEW)
    income_categories = set()
    for d in forecast_data[::12]:
        income_categories.update(d['income_category_breakdown'].keys())
    
    # Category colors for income
    income_cat_colors = [
        '#198754', '#0d6efd', '#6f42c1', '#20c997',
        '#0dcaf0', '#6610f2', '#d63384', '#ffc107',
    ]
    
    income_evo_datasets = []
    for idx, cat in enumerate(sorted(list(income_categories))):
        cat_data = [float(d['income_category_breakdown'].get(cat, 0)) * 12 for d in forecast_data[::12]]
        color = income_cat_colors[idx % len(income_cat_colors)]
        income_evo_datasets.append({
            'label': cat,
            'data': cat_data,
            'backgroundColor': color,
            'stack': 'income',
        })
    
    # One-Time Events dataset — aggregate per year
    one_time_yearly = []
    one_time_tooltips = []
    for d in forecast_data[::12]:
        year = d['date'].year
        # Collect all events for this year
        year_events = []
        year_total = 0.0
        for md in forecast_data:
            if md['date'].year == year and md['one_time_events']:
                for evt in md['one_time_events']:
                    year_events.append(evt)
                    year_total += evt['value']
        one_time_yearly.append(year_total)
        one_time_tooltips.append(year_events)
    
    income_evo_datasets.append({
        'label': str(_('One-Time Events')),
        'data': one_time_yearly,
        'backgroundColor': 'rgba(255, 165, 0, 0.85)',
        'borderColor': '#ff8c00',
        'borderWidth': 2,
        'stack': 'events',
        'tooltipData': one_time_tooltips,
    })

    chart_datasets = {
        'net_worth_chart': {
            'labels': labels_yearly,
            'datasets': [
                {'label': 'Nominal', 'data': net_worth_nominal, 'borderColor': 'blue', 'fill': True},
                {'label': 'Real', 'data': net_worth_real, 'borderColor': 'green', 'borderDash': [5, 5], 'fill': False},
            ]
        },
        'cashflow_chart': {
             'labels': labels_yearly,
             'datasets': [
                 {'label': str(_('Income')), 'data': income_yearly, 'backgroundColor': 'rgba(25, 135, 84, 0.7)', 'order': 2},
                 {'label': str(_('Expenses')), 'data': expenses_yearly, 'backgroundColor': 'rgba(220, 53, 69, 0.7)', 'order': 2},
                 {'label': str(_('Net Savings')), 'data': net_savings_yearly, 'type': 'line', 'borderColor': '#0d6efd', 'borderWidth': 2, 'fill': False, 'pointRadius': 3, 'order': 1},
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
            'datasets': [{'data': budget_data, 'backgroundColor': ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0']}]
        },
    }

    chart_datasets['inflation_monitor_chart'] = {
        'labels': inflation_data['labels'],
        'datasets': [
            {'label': str(_('Nominal Value')), 'data': inflation_data['nominal'], 'borderColor': '#0d6efd', 'fill': False},
            {'label': str(_('Real Value (Purchasing Power)')), 'data': inflation_data['real'], 'borderColor': '#198754', 'fill': False},
            {
                'label': str(_('Purchasing Power Loss')), 
                'data': inflation_data['loss'], 
                'backgroundColor': 'rgba(220, 53, 69, 0.5)', 
                'type': 'bar',
                'percentData': inflation_data['loss_percent']
            }
        ]
    }

    # Key Metrics for Summary Panels
    if forecast_data:
        first_month = forecast_data[0]
        last_month = forecast_data[-1]
        current_net_worth = first_month.get('nominal_net_worth', 0)
        projected_net_worth = last_month.get('nominal_net_worth', 0)
        current_monthly_income = first_month.get('monthly_income', 0)
        current_monthly_expenses = first_month.get('monthly_expenses', 0)
        current_pensions_total = first_month.get('pension_total', 0)
        current_assets_total = first_month.get('asset_total', 0)
    else:
        current_net_worth = 0
        projected_net_worth = 0
        current_monthly_income = 0
        current_monthly_expenses = 0
        current_pensions_total = 0
        current_assets_total = 0
    
    simulated_end_age = int(profile.simulation_max_age)
    
    # 7. Table Gadget Data (Monthly Normalized)
    table_data_income = []
    for cf in user.cash_flows.filter(is_income=True):
        amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
        table_data_income.append({'name': cf.name, 'amount': float(amt), 'category': cf.category.name if cf.category else _('Uncategorized')})

    table_data_expense = []
    for cf in user.cash_flows.filter(is_income=False):
        amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
        table_data_expense.append({'name': cf.name, 'amount': float(amt), 'category': cf.category.name if cf.category else _('Uncategorized')})

    table_data_asset = []
    for a in user.assets.filter(withdrawal_amount__gt=0):
        table_data_asset.append({'name': a.name, 'amount': float(a.withdrawal_amount), 'category': _('Withdrawal')})

    table_data_pension = []
    for p in user.pensions.filter(monthly_contribution__gt=0):
        table_data_pension.append({'name': p.provider, 'amount': float(p.monthly_contribution), 'category': _('Contribution')})

    table_data_event = []
    for e in user.events.all():
        amt = e.value / 12 # Prorated monthly
        table_data_event.append({'name': e.name, 'amount': float(amt), 'category': _('One-Time')})

    table_datasets = {
        'income_table_widget': table_data_income,
        'expense_table_widget': table_data_expense,
        'asset_table_widget': table_data_asset,
        'pension_table_widget': table_data_pension,
        'event_table_widget': table_data_event,
    }

    # Key Metrics for Summary Panels

    context = {
        'profile': profile,
        'currency': profile.currency,
        'layout': layout,
        'summary_layout': summary_layout,
        'layout_json': json.dumps(layout, cls=DjangoJSONEncoder),
        'summary_layout_json': json.dumps(summary_layout, cls=DjangoJSONEncoder),
        'available_charts': AVAILABLE_CHARTS,
        'summary_widgets': SUMMARY_WIDGETS,
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
        'simulation_config': simulation_config,
        'table_datasets': table_datasets,
    }
    
    if request.headers.get('HX-Request') and 'config_update' not in request.POST:
        return render(request, 'finance/partials/dashboard_charts.html', context)
        
    return render(request, 'finance/dashboard.html', context)
