from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('import/', views.upload_bank_transactions, name='import_transactions'),
    path('import/review/<int:batch_id>/', views.review_bank_transactions, name='review_transactions'),
    path('import/confirm/<int:transaction_id>/', views.confirm_bank_transaction, name='confirm_transaction'),
    path('import/apply/<int:batch_id>/', views.apply_import_batch, name='apply_import'),
    path('import/progress/', views.get_import_progress, name='import_progress'),
    path('import/processing/', views.import_processing, name='import_processing'),
    path('import/delete-all/', views.delete_all_temporary_data, name='delete_all_temporary_data'),
    path('ai-status/', views.ai_status, name='ai_status'),
    path('import/filters/', views.import_filters_list, name='import_filters_list'),
    path('import/filters/add/', views.add_import_filter, name='add_import_filter'),
    path('import/filters/delete/<int:filter_id>/', views.delete_import_filter, name='delete_import_filter'),
]
