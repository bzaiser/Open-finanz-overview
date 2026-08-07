from django.urls import path
from . import views, wizard_views

app_name = 'finance'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('import/', views.upload_bank_transactions, name='import_transactions'),
    path('import/review/<int:batch_id>/', views.review_bank_transactions, name='review_transactions'),
    path('import/confirm/<int:transaction_id>/', views.confirm_bank_transaction, name='confirm_transaction'),
    path('import/apply/<int:batch_id>/', views.apply_import_batch, name='apply_import'),
    path('import/progress/', views.get_import_progress, name='import_progress'),
    path('import/processing/', views.import_processing, name='import_processing'),
    path('import/delete/<int:batch_id>/', views.delete_import_batch, name='delete_import_batch'),
    path('import/delete-all/', views.delete_all_temporary_data, name='delete_all_temporary_data'),
    path('import/delete-history/', views.delete_all_import_history, name='delete_all_import_history'),
    path('ai-status/', views.ai_status, name='ai_status'),
    path('import/filters/', views.import_filters_list, name='import_filters_list'),
    path('import/filters/add/', views.add_import_filter, name='add_import_filter'),
    path('import/filters/edit/<int:filter_id>/', views.edit_import_filter, name='edit_import_filter'),
    path('import/filters/delete/<int:filter_id>/', views.delete_import_filter, name='delete_import_filter'),
    path('import/group/<int:batch_id>/', views.import_search_as_group, name='import_search_as_group'),
    path('category/quick-create/', views.quick_create_category, name='quick_create_category'),
    path('cash-flow/quick-create/', views.quick_create_cash_flow, name='quick_create_cash_flow'),
    path('cash-flows/', views.cash_flow_list, name='cash_flow_list'),
    path('cash-flows/save/', views.cash_flow_save, name='cash_flow_add'),
    path('cash-flows/save/<int:pk>/', views.cash_flow_save, name='cash_flow_edit'),
    path('cash-flows/delete/<int:pk>/', views.cash_flow_delete, name='cash_flow_delete'),
    path('cash-flows/annual-adjustment/', views.cash_flow_annual_adjustment, name='cash_flow_annual_adjustment'),
    path('pensions/', views.pension_plan_view, name='pension_plan'),
    path('pensions/save/', views.pension_save, name='pension_add'),
    path('pensions/save/<int:pk>/', views.pension_save, name='pension_edit'),
    path('pensions/delete/<int:pk>/', views.pension_delete, name='pension_delete'),
    path('pensions/snapshot/save/', views.pension_snapshot_save, name='pension_snapshot_save'),
    path('wizard/', wizard_views.wizard_page_view, name='setup_wizard'),
    path('wizard/save/', wizard_views.wizard_save_api, name='setup_wizard_save'),
    path('dynamic-theme.css', views.dynamic_theme_css, name='dynamic_theme_css'),
]
