from django.core.management.base import BaseCommand
from core.models import CustomUser, UserProfile
from finance.models import (
    Asset, CashFlowSource, OneTimeEvent, Category, 
    PhysicalAsset, RealEstate, Loan, Pension
)
from datetime import date, timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds the database with a realistic and comprehensive set of demo data'

    def handle(self, *args, **kwargs):
        # 1. Create or Reset Demo User
        username = 'demo'
        password = 'demo'
        
        user, created = CustomUser.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True # Full access for demo
        user.save()
        
        # Ensure UserProfile exists with a nice purple gradient
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.gradient_start = "#6610f2"
        profile.gradient_end = "#0d6efd"
        profile.save()

        # 2. Clear existing data for this user
        Asset.objects.filter(user=user).delete()
        CashFlowSource.objects.filter(user=user).delete()
        OneTimeEvent.objects.filter(user=user).delete()
        PhysicalAsset.objects.filter(user=user).delete()
        RealEstate.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()

        self.stdout.write(self.style.NOTICE(f'Cleaning up and seeding for user "{username}"...'))

        # 3. Create Categories
        cat_names = ['Gehalt', 'Miete', 'Lebensmittel', 'Mobilität', 'Freizeit', 'Versicherung', 'Investition', 'Immobilie']
        cats = {name: Category.objects.get_or_create(name=name)[0] for name in cat_names}

        # 4. Assets (Liquid & Stocks)
        Asset.objects.create(user=user, name='Girokonto (DKB)', value=Decimal('2850.00'))
        Asset.objects.create(user=user, name='Tagesgeld (Notgroschen)', value=Decimal('15000.00'), growth_rate=Decimal('3.5'))
        Asset.objects.create(user=user, name='Vanguard FTSE All-World', value=Decimal('42500.00'), growth_rate=Decimal('7.0'))
        Asset.objects.create(user=user, name='Bitcoin (Cold Wallet)', value=Decimal('8200.00'), growth_rate=Decimal('15.0'))

        # 5. Physical Assets (Sachwerte)
        PhysicalAsset.objects.create(user=user, name='VW Golf VIII', value=Decimal('22000.00'), appreciation_rate=Decimal('-5.0'))
        PhysicalAsset.objects.create(user=user, name='Rolex Submariner', value=Decimal('11200.00'), appreciation_rate=Decimal('3.0'))

        # 6. Real Estate & Corresponding Loan
        apartment = RealEstate.objects.create(
            user=user, 
            name='ETW Berlin-Pankow', 
            property_value=Decimal('315000.00'),
            appreciation_rate=Decimal('2.5'),
            rental_income_monthly=Decimal('950.00'),
            maintenance_costs_monthly=Decimal('250.00')
        )

        Loan.objects.create(
            user=user,
            name='Immobiliendarlehen Pankow',
            nominal_amount=Decimal('220000.00'),
            interest_rate=Decimal('1.85'),
            monthly_installment=Decimal('850.00'),
            start_date=date(2022, 1, 1)
        )

        # 7. Pensions
        Pension.objects.create(user=user, provider='Gesetzliche Rentenversicherung', expected_payout_at_retirement=Decimal('1850.00'), start_payout_date=date(2055, 1, 1), is_indexed=True)
        Pension.objects.create(user=user, provider='Allianz Riester Rente', expected_payout_at_retirement=Decimal('320.00'), start_payout_date=date(2055, 1, 1), is_indexed=True)

        # 8. CashFlow - Incomes
        CashFlowSource.objects.create(
            user=user, name='Hauptjob Software Engineer', value=Decimal('3800.00'),
            is_income=True, category=cats['Gehalt'], frequency='monthly', is_inflation_adjusted=True
        )
        CashFlowSource.objects.create(
            user=user, name='Nebentätigkeit Beratung', value=Decimal('450.00'),
            is_income=True, category=cats['Gehalt'], frequency='monthly'
        )

        # 9. CashFlow - Expenses
        expenses = [
            ('Warmmiete Wohnung', 1250.00, 'Miete'),
            ('Lebensmittel & Haushalt', 550.00, 'Lebensmittel'),
            ('Strom & Gas', 140.00, 'Miete'),
            ('Internet & Handy', 65.00, 'Freizeit'),
            ('Netflix / Spotify / Disney', 35.00, 'Freizeit'),
            ('Fitnessstudio Mitgliedschaft', 45.00, 'Freizeit'),
            ('Haftpflicht / Rechtsschutz', 25.00, 'Versicherung'),
            ('ÖPNV Ticket', 49.00, 'Mobilität'),
        ]
        for name, val, cat in expenses:
            CashFlowSource.objects.create(
                user=user, name=name, value=Decimal(str(val)),
                is_income=False, category=cats[cat], frequency='monthly'
            )

        # 10. OneTimeEvents
        today = date.today()
        OneTimeEvent.objects.create(
            user=user, name='Jahresbonus', value=Decimal('4500.00'),
            date=date(today.year, 3, 15), description='Performance Bonus Vorjahr'
        )
        OneTimeEvent.objects.create(
            user=user, name='Weltreise (Sabbatical)', value=Decimal('-12000.00'),
            date=date(today.year + 1, 6, 1), description='3 Monate Auszeit'
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded realistic data for user "{username}" (Password: "{password}")'))
