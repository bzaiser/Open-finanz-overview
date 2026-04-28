from django.apps import AppConfig


class FinanceConfig(AppConfig):
    name = 'finance'

    def ready(self):
        import finance.signals
        from django.contrib import admin
        admin.site.site_header = "Finanzplan Admin"
        admin.site.site_title = "Finanzplan"
        admin.site.index_title = "Finanzplan Admin"
