from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from finance.models import Profile, Asset, CashFlowSource, OneTimeEvent, Category
from datetime import date
from decimal import Decimal
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seeds the database with demo data for user "demo" with password "demo"'

    def handle(self, *args, **kwargs):
        # 1. Create or Reset Demo User
        username = 'demo'
        password = 'demo'
        
        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True # Allow admin access for demo
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created user "{username}"'))
        else:
            self.stdout.write(self.style.WARNING(f'Reset password for existing user "{username}"'))

        # 2. Reset existing data for this user to ensure clean state
        Asset.objects.filter(user=user).delete()
        CashFlowSource.objects.filter(user=user).delete()
        OneTimeEvent.objects.filter(user=user).delete()

        # 3. Create Categories (if missing)
        cats = {
            'Gehalt': 'Gehalt',
            'Miete': 'Miete',
            'Lebensmittel': 'Lebensmittel',
            'ETF': 'Investitionen',
            'Versicherung': 'Versicherungen',
            'Freizeit': 'Freizeit',
        }
        category_objects = {}
        for name, internal_name in cats.items():
            cat, _ = Category.objects.get_or_create(name=name)
            category_objects[name] = cat

        # 4. Create Assets
        Asset.objects.create(
            user=user, name='Girokonto', 
            value=Decimal('4200.00'), 
            asset_type='Bank'
        )
        Asset.objects.create(
            user=user, name='Tagesgeld', 
            value=Decimal('12000.00'), 
            asset_type='Bank'
        )
        Asset.objects.create(
            user=user, name='MSCI World ETF', 
            value=Decimal('35000.00'), 
            asset_type='Stock',
            expected_annual_return=Decimal('7.0')
        )

        # 5. Create Income (CashFlowSource)
        CashFlowSource.objects.create(
            user=user, name='Hauptberuf Gehalt',
            value=Decimal('3200.00'),
            is_income=True,
            category=category_objects['Gehalt'],
            start_date=date(2023, 1, 1),
            frequency='monthly',
            is_inflation_adjusted=True
        )

        # 6. Create Expenses (CashFlowSource)
        CashFlowSource.objects.create(
            user=user, name='Miete & Nebenkosten',
            value=Decimal('1150.00'),
            is_income=False,
            category=category_objects['Miete'],
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='Lebensmittel & Haushalt',
            value=Decimal('600.00'),
            is_income=False,
            category=category_objects['Lebensmittel'],
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='ETF Sparplan',
            value=Decimal('500.00'),
            is_income=False,
            category=category_objects['ETF'],
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='KFZ-Versicherung',
            value=Decimal('450.00'),
            is_income=False,
            category=category_objects['Versicherung'],
            start_date=date(2024, 1, 1),
            frequency='yearly'
        )

        # 7. Create OneTimeEvents (Past and Future)
        today = date.today()
        OneTimeEvent.objects.create(
            user=user, name='Steuerrückerstattung',
            value=Decimal('1200.00'),
            date=date(today.year, 8, 15),
            description='Erwartete Rückerstattung für 2024'
        )
        OneTimeEvent.objects.create(
            user=user, name='Urlaub Japan',
            value=Decimal('-3500.00'),
            date=date(today.year, 10, 10),
            description='Geplante Rundreise'
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with demo data.'))
