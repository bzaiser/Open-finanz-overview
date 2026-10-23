from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import CustomUser, UserProfile
from finance.models import (
    Asset, CashFlowSource, OneTimeEvent, Category, RealEstate, Loan, Pension, AssetSnapshot
)
from datetime import date
from decimal import Decimal
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Seeds the database with comprehensive demo data for user "demo" with password "demo"'

    def handle(self, *args, **kwargs):
        # 1. Create or Reset Demo User
        username = 'demo'
        password = 'demo'
        
        user, created = CustomUser.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True # Allow admin access for demo
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created user "{username}"'))
        else:
            self.stdout.write(self.style.WARNING(f'Reset password for existing user "{username}"'))

        # Ensure UserProfile exists with simulation and partner parameters
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Demo Benutzer & Partner"
        profile.birth_date = date(1985, 4, 12)
        profile.retirement_age = 67
        profile.partner_name = "Partner"
        profile.partner_birth_date = date(1987, 8, 20)
        profile.partner_retirement_age = 67
        profile.target_pension_payout = Decimal("3200.00")
        profile.inflation_rate = Decimal("2.00")
        profile.pension_increase = Decimal("1.50")
        profile.save()

        # 2. Reset existing data for this user to ensure clean state
        Asset.objects.filter(user=user).delete()
        CashFlowSource.objects.filter(user=user).delete()
        OneTimeEvent.objects.filter(user=user).delete()
        RealEstate.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()
        AssetSnapshot.objects.filter(user=user).delete()

        # 3. Create Categories (if missing)
        cats = {
            'Gehalt': ('gehalt', 'Gehalt', '#11ff00'),
            'Miete': ('wohnen-haushalt', 'Wohnen & Haushalt', '#0d6efd'),
            'Lebensmittel': ('lebensmittel', 'Lebensmittel', '#fd7e14'),
            'Investitionen': ('investitionen-sparen', 'Investitionen & Sparen', '#6f42c1'),
            'Versicherungen': ('versicherungen', 'Versicherungen', '#20c997'),
            'Freizeit': ('freizeit-reisen', 'Freizeit & Reisen', '#ffc107'),
        }
        category_objects = {}
        for key, (slug_val, name, col) in cats.items():
            cat = Category.objects.filter(slug=slug_val).first()
            if not cat:
                cat = Category.objects.filter(name=name).first()
            if not cat:
                cat = Category.objects.create(slug=slug_val, name=name, color=col)
            category_objects[key] = cat

        # 4. Create Assets
        Asset.objects.create(
            user=user, name='Girokonto Sparkasse', 
            value=Decimal('4200.00'), 
        )
        Asset.objects.create(
            user=user, name='Tagesgeld Notgroschen', 
            value=Decimal('15000.00'), 
            growth_rate=Decimal('2.5')
        )
        Asset.objects.create(
            user=user, name='MSCI World ETF', 
            value=Decimal('48000.00'), 
            growth_rate=Decimal('7.0')
        )

        # 5. Create Income (CashFlowSource) mit Vorlagen-IDs
        CashFlowSource.objects.create(
            user=user, name='Hauptberuf Gehalt',
            value=Decimal('3400.00'),
            is_income=True,
            category=category_objects['Gehalt'],
            template_id='inc_gehalt',
            start_date=date(2023, 1, 1),
            frequency='monthly',
            is_inflation_adjusted=True
        )
        CashFlowSource.objects.create(
            user=user, name='Partner Gehalt (Teilzeit)',
            value=Decimal('1600.00'),
            is_income=True,
            category=category_objects['Gehalt'],
            template_id='inc_minijob',
            start_date=date(2023, 1, 1),
            frequency='monthly',
            is_inflation_adjusted=True
        )

        # 6. Create Expenses (CashFlowSource) mit Vorlagen-IDs
        CashFlowSource.objects.create(
            user=user, name='Kaltmiete & Hausgeld',
            value=Decimal('950.00'),
            is_income=False,
            category=category_objects['Miete'],
            template_id='exp_kaltmiete',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='Nebenkosten & Heizung',
            value=Decimal('280.00'),
            is_income=False,
            category=category_objects['Miete'],
            template_id='exp_nebenkosten',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='Lebensmittel & Haushalt',
            value=Decimal('650.00'),
            is_income=False,
            category=category_objects['Lebensmittel'],
            template_id='exp_lebensmittel',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='ETF Sparplan',
            value=Decimal('500.00'),
            is_income=False,
            category=category_objects['Investitionen'],
            template_id='exp_etf_sparplan',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='KFZ-Versicherung',
            value=Decimal('480.00'),
            is_income=False,
            category=category_objects['Versicherungen'],
            template_id='exp_kfz_versicherung',
            start_date=date(2024, 1, 1),
            frequency='yearly'
        )
        CashFlowSource.objects.create(
            user=user, name='Privathaftpflicht & Hausrat',
            value=Decimal('180.00'),
            is_income=False,
            category=category_objects['Versicherungen'],
            template_id='exp_haftpflicht',
            start_date=date(2024, 1, 1),
            frequency='yearly'
        )

        # 7. Create RealEstate and Loan
        re = RealEstate.objects.create(
            user=user,
            name='Eigentumswohnung',
            property_value=Decimal('320000.00'),
            appreciation_rate=Decimal('2.0'),
            location='Innenstadt',
            maintenance_costs_monthly=Decimal('120.00')
        )
        Loan.objects.create(
            user=user,
            name='Wohnungsdarlehen',
            provider='Bank',
            nominal_amount=Decimal('180000.00'),
            interest_rate=Decimal('2.4'),
            monthly_installment=Decimal('850.00'),
            start_date=date(2020, 1, 1),
            end_date=date(2045, 1, 1)
        )

        # 8. Create Pensions
        Pension.objects.create(
            user=user,
            provider='Deutsche Rentenversicherung (Demo)',
            pension_type='statutory',
            pension_points=Decimal('38.4000'),
            point_value=Decimal('39.32'),
            social_deduction_rate=Decimal('11.50'),
            expected_payout_at_retirement=Decimal('1336.00'),
            retirement_age=67,
            start_payout_date=date(2052, 5, 1)
        )
        Pension.objects.create(
            user=user,
            provider='Betriebliche Altersversorgung (bAV)',
            pension_type='capital',
            current_value=Decimal('24000.00'),
            monthly_contribution=Decimal('150.00'),
            growth_rate=Decimal('3.50'),
            expected_payout_at_retirement=Decimal('280.00'),
            retirement_age=67,
            start_payout_date=date(2052, 6, 1)
        )

        # 9. Create OneTimeEvents (Past and Future)
        today = date.today()
        OneTimeEvent.objects.create(
            user=user, name='Steuerrückerstattung',
            value=Decimal('1200.00'),
            date=date(today.year, 8, 15),
            description='Erwartete Rückerstattung'
        )
        OneTimeEvent.objects.create(
            user=user, name='Urlaub',
            value=Decimal('-2500.00'),
            date=date(today.year, 10, 10),
            description='Sommerurlaub'
        )

        self.stdout.write(self.style.SUCCESS('[OK] Successfully seeded database with comprehensive demo data.'))
