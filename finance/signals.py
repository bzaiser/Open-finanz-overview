from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils.translation import gettext_noop as _
from .models import Category

@receiver(post_migrate)
def create_system_categories(sender, **kwargs):
    if sender.name == 'finance':
        # Define system categories with their slugs and default colors
        # We use gettext_noop to mark for translation but keep the DB string stable
        system_cats = [
            {'name': 'Kredit', 'slug': 'kredit', 'color': '#dc3545'},
            {'name': 'Rente', 'slug': 'rente', 'color': '#6f42c1'},
            {'name': 'Sparen', 'slug': 'sparen', 'color': '#0d6efd'},
            {'name': 'Immobilien', 'slug': 'immobilien', 'color': '#20c997'},
            {'name': 'Sachwerte', 'slug': 'sachwerte', 'color': '#8a2be2'},
            {'name': 'Vermögen', 'slug': 'vermoegen', 'color': '#198754'},
        ]
        
        for cat_data in system_cats:
            cat, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'color': cat_data['color'],
                    'is_system': True
                }
            )
            if not created and not cat.is_system:
                cat.is_system = True
                cat.save()
