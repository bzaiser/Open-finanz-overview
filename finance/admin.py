from django.contrib import admin
from .models import Category, CashFlowSource, Asset, OneTimeEvent, Pension

@admin.register(Pension)
class PensionAdmin(admin.ModelAdmin):
    list_display = ('provider', 'user', 'current_value', 'monthly_contribution')
    search_fields = ('provider', 'user__username')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    prepopulated_fields = {'slug': ('name',)}

import datetime
import calendar
from django.utils.translation import gettext_lazy as _

@admin.action(description=_("Auswahl duplizieren & Datum hochzählen"))
def duplicate_and_increment_cashflow(modeladmin, request, queryset):
    count = 0
    for obj in queryset:
        obj.pk = None  # Duplicate record
        
        def add_months(sourcedate, months):
            if not sourcedate: return None
            month = sourcedate.month - 1 + months
            year = int(sourcedate.year + month // 12)
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return datetime.date(year, month, day)

        def add_years(sourcedate, years):
            if not sourcedate: return None
            try:
                return sourcedate.replace(year=sourcedate.year + years)
            except ValueError:
                # Handle leap years (Feb 29)
                return sourcedate.replace(year=sourcedate.year + years, day=28)
                
        if obj.frequency == 'yearly':
            obj.start_date = add_years(obj.start_date, 1)
            obj.end_date = add_years(obj.end_date, 1)
        elif obj.frequency == 'monthly':
            obj.start_date = add_months(obj.start_date, 1)
            obj.end_date = add_months(obj.end_date, 1)
            
        obj.save()
        count += 1
    
    modeladmin.message_user(request, f"{count} Datensätze erfolgreich dupliziert und aktualisiert.")

class YearListFilter(admin.SimpleListFilter):
    title = _('Jahr')
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        # Hole alle verwendeten Jahre aus der Datenbank, absteigend sortiert
        qs = model_admin.get_queryset(request)
        dates = qs.values_list('start_date', flat=True)
        years = set([d.year for d in dates if d])
        return [(str(y), str(y)) for y in sorted(years, reverse=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(start_date__year=self.value())
        return queryset

@admin.register(CashFlowSource)
class CashFlowSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'value', 'category', 'is_income', 'frequency', 'start_date', 'end_date')
    list_filter = (YearListFilter, 'is_income', 'frequency', 'user', 'category')
    search_fields = ('name',)
    actions = [duplicate_and_increment_cashflow]

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'value', 'growth_rate')
    list_filter = ('user',)
    search_fields = ('name',)

@admin.register(OneTimeEvent)
class OneTimeEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'value', 'date')
    list_filter = ('user',)
    search_fields = ('name',)
