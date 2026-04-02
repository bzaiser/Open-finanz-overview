from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from .services import SimulationEngine
from .models import (
    Asset, CashFlowSource, OneTimeEvent, Pension, Category, 
    ImportBatch, PendingTransaction
)
from .forms import BankImportForm
from .import_services import ExcelParserService
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.core.files.storage import default_storage
import json
import os
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
    'asset_table_widget': {'title': _('Asset Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'pension_table_widget': {'title': _('Pension Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
    'event_table_widget': {'title': _('One-Time Event Table'), 'type': 'table', 'default_width': 6, 'default_height': 'small'},
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
    
    # Helper for safe merging of defaults
    def safe_merge(user_data, defaults):
        if not user_data: return defaults
        return {**defaults, **user_data}

    # Initialize or get Dashboard Config
    dashboard_config = profile.dashboard_config or {}
    
    # 2. Extract configurations with safe defaults
    layout = dashboard_config.get('layout', DEFAULT_LAYOUT)

    summary_layout = dashboard_config.get('summary_layout', [
        {'id': 'current_assets', 'visible': True, 'bg_color': '#0d6efd', 'text_color': '#ffffff', 'order': 1},
        {'id': 'monthly_income', 'visible': True, 'bg_color': '#198754', 'text_color': '#ffffff', 'order': 2},
        {'id': 'monthly_expenses', 'visible': True, 'bg_color': '#dc3545', 'text_color': '#ffffff', 'order': 3},
        {'id': 'total_pensions', 'visible': True, 'bg_color': '#0dcaf0', 'text_color': '#ffffff', 'order': 4},
    ])

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
                
                table_style_json = request.POST.get('table_style_json')
                if table_style_json:
                    new_table_config = json.loads(table_style_json)
                    dashboard_config['table_style'] = new_table_config
                
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
            'borderColor': color,
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

    # 3. Budget Pie (Current month breakdown)
    today = timezone.now().date()
    current_month_data = None
    if forecast_data:
        # Find the point corresponding to the current month/year
        for d in forecast_data:
            if d['date'].year == today.year and d['date'].month == today.month:
                current_month_data = d
                break
        
        # Fallback to the first month if today is not in the forecast
        if not current_month_data:
            current_month_data = forecast_data[0]
            
        budget_labels = list(current_month_data['category_breakdown'].keys())
        budget_data = list(current_month_data['category_breakdown'].values())
        budget_colors = [category_color_map.get(lbl, fallback_colors[i % len(fallback_colors)]) for i, lbl in enumerate(budget_labels)]
    else:
        budget_labels = []
        budget_data = []
        budget_colors = []

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

    inflation_data = {
        'labels': labels_yearly,
        'nominal': net_worth_nominal,
        'real': net_worth_real,
        'loss': inflation_loss,
        'loss_percent': inflation_loss_percent
    }

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
            'datasets': [{'data': budget_data, 'backgroundColor': budget_colors}]
        },
        'inflation_monitor_chart': {
            'labels': labels_yearly,
            'datasets': [
                {'label': str(_('Nominal Value')), 'data': net_worth_nominal, 'borderColor': '#0d6efd', 'fill': False},
                {'label': str(_('Real Value (Purchasing Power)')), 'data': net_worth_real, 'borderColor': '#198754', 'fill': False},
                {
                    'label': str(_('Purchasing Power Loss')), 
                    'data': inflation_loss, 
                    'backgroundColor': 'rgba(220, 53, 69, 0.5)', 
                    'type': 'bar',
                    'percentData': inflation_loss_percent
                }
            ]
        }
    }

    # Key Metrics for Summary Panels (Current situation)
    if current_month_data:
        last_month = forecast_data[-1]
        current_net_worth = current_month_data.get('nominal_net_worth', 0)
        projected_net_worth = last_month.get('nominal_net_worth', 0)
        current_monthly_income = current_month_data.get('monthly_income', 0)
        current_monthly_expenses = current_month_data.get('monthly_expenses', 0)
        current_pensions_total = current_month_data.get('pension_total', 0)
        current_assets_total = current_month_data.get('asset_total', 0)
    else:
        current_net_worth = 0
        projected_net_worth = 0
        current_monthly_income = 0
        current_monthly_expenses = 0
        current_pensions_total = 0
        current_assets_total = 0
    
    simulated_end_age = int(profile.simulation_max_age)
    
    # 7. Table Gadget Data (Monthly Normalized)
    continuous_label = _('Continuous')
    table_data_income = []
    # Direct income
    for cf in user.cash_flows.filter(is_income=True):
        amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
        year = str(cf.start_date.year) if cf.start_date else continuous_label
        table_data_income.append({
            'name': cf.name, 
            'amount': float(amt), 
            'category': cf.category.name if cf.category else _('Uncategorized'),
            'type': _('Manual'),
            'year': year
        })
    # Asset withdrawals (Income)
    for a in user.assets.filter(withdrawal_amount__gt=0):
        year = str(a.withdrawal_start_date.year) if a.withdrawal_start_date else continuous_label
        table_data_income.append({
            'name': f"{_('Withdrawal')}: {a.name}", 
            'amount': float(a.withdrawal_amount), 
            'category': _('Asset'),
            'type': _('Asset'),
            'year': year
        })

    table_data_expense = []
    # Direct expenses
    for cf in user.cash_flows.filter(is_income=False):
        amt = cf.value if cf.frequency == 'monthly' else cf.value / 12
        year = str(cf.start_date.year) if cf.start_date else continuous_label
        table_data_expense.append({
            'name': cf.name, 
            'amount': float(amt), 
            'category': cf.category.name if cf.category else _('Uncategorized'),
            'type': _('Manual'),
            'year': year
        })
    # Pension contributions (Expense)
    for p in user.pensions.filter(monthly_contribution__gt=0):
        # Pensions are usually continuous until retirement
        table_data_expense.append({
            'name': f"{_('Contribution')}: {p.provider}", 
            'amount': float(p.monthly_contribution), 
            'category': _('Pension'),
            'type': _('Pension'),
            'year': continuous_label
        })

    table_data_asset = []
    for a in user.assets.all():
        table_data_asset.append({
            'name': a.name, 
            'amount': float(a.value), 
            'category': _('Asset'),
            'rate': f"{a.growth_rate}%",
            'year': continuous_label
        })

    table_data_pension = []
    for p in user.pensions.all():
        year = str(p.start_payout_date.year) if p.start_payout_date else continuous_label
        table_data_pension.append({
            'name': p.provider, 
            'amount': float(p.current_value), 
            'category': _('Pension'),
            'contribution': float(p.monthly_contribution),
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

    context = {
        'profile': profile,
        'currency': profile.currency or 'EUR',
        'layout': layout,
        'summary_layout': summary_layout,
        'layout_json': json.dumps(layout, cls=DjangoJSONEncoder),
        'summary_layout_json': json.dumps(summary_layout, cls=DjangoJSONEncoder),
        'available_charts': AVAILABLE_CHARTS,
        'summary_widgets': SUMMARY_WIDGETS,
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
        'simulation_config': simulation_config,
        'table_config': table_config,
        'table_datasets': table_datasets,
        'debug_lang': translation.get_language(),
        'debug_trans_test': translation.gettext('Help'),
    }
    

@login_required
def upload_bank_transactions(request):
    if request.method == 'POST':
        form = BankImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            # Save file temporarily
            file_name = default_storage.save(f"tmp/{uploaded_file.name}", uploaded_file)
            file_path = os.path.join(settings.MEDIA_ROOT, file_name)
            
            try:
                parser = ExcelParserService(request.user, file_path, uploaded_file.name)
                batch = parser.parse_and_categorize()
                messages.success(request, _("Datei erfolgreich eingelesen. Bitte überprüfe die Kategorisierung."))
                return redirect('review_transactions', batch_id=batch.id)
            except Exception as e:
                messages.error(request, f"Fehler beim Import: {str(e)}")
            finally:
                # Cleanup
                if os.path.exists(file_path):
                    os.remove(file_path)
    else:
        form = BankImportForm()
    
    return render(request, 'finance/import_upload.html', {'form': form})

@login_required
def review_bank_transactions(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id, user=request.user)
    transactions = batch.transactions.all().order_by('date')
    categories = Category.objects.all()
    
    return render(request, 'finance/import_review.html', {
        'batch': batch,
        'transactions': transactions,
        'categories': categories
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
            
    batch.is_applied = True
    batch.save()
    
    messages.success(request, _(f"Import abgeschlossen: {count_one_time} Einzelbuchungen und {count_recurring} regelmäßige Zahlungen erstellt."))
    return redirect('dashboard')
