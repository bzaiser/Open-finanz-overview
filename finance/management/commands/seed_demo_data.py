from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import CustomUser, UserProfile
from finance.models import (
    Asset, CashFlowSource, OneTimeEvent, Category, RealEstate, Loan, Pension,
    AssetSnapshot, PropertyComponent
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
        user.is_staff = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created user "{username}"'))
        else:
            self.stdout.write(self.style.WARNING(f'Reset password for existing user "{username}"'))

        # Ensure UserProfile exists with simulation and partner parameters
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Demo User & Partner"
        profile.birth_date = date(1985, 4, 12)
        profile.retirement_age = 67
        profile.partner_name = "Partner"
        profile.partner_birth_date = date(1987, 8, 20)
        profile.partner_retirement_age = 67
        profile.target_pension_payout = Decimal("3200.00")
        profile.inflation_rate = Decimal("2.00")
        profile.pension_increase = Decimal("1.50")
        from core.models import get_default_dashboard_config
        profile.dashboard_config = get_default_dashboard_config()
        profile.save()

        # 2. Reset existing data for this user to ensure clean state
        PropertyComponent.objects.filter(real_estate__user=user).delete()
        Asset.objects.filter(user=user).delete()
        CashFlowSource.objects.filter(user=user).delete()
        OneTimeEvent.objects.filter(user=user).delete()
        RealEstate.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()
        AssetSnapshot.objects.filter(user=user).delete()

        # 3. Create Categories (if missing)
        cats = {
            'Salary': ('gehalt', 'Gehalt', '#11ff00'),
            'Rent': ('wohnen-haushalt', 'Wohnen & Haushalt', '#0d6efd'),
            'Groceries': ('lebensmittel', 'Lebensmittel', '#fd7e14'),
            'Investments': ('investitionen-sparen', 'Investitionen & Sparen', '#6f42c1'),
            'Insurance': ('versicherungen', 'Versicherungen', '#20c997'),
            'Leisure': ('freizeit-reisen', 'Freizeit & Reisen', '#ffc107'),
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
            user=user, name='Checking Account (Sparkasse)',
            value=Decimal('4200.00'),
        )
        Asset.objects.create(
            user=user, name='Emergency Fund (Overnight Account)',
            value=Decimal('15000.00'),
            growth_rate=Decimal('2.5')
        )
        Asset.objects.create(
            user=user, name='MSCI World ETF',
            value=Decimal('48000.00'),
            growth_rate=Decimal('7.0')
        )

        # 5. Create Income (CashFlowSource)
        CashFlowSource.objects.create(
            user=user, name='Primary Salary',
            value=Decimal('3400.00'),
            is_income=True,
            category=category_objects['Salary'],
            template_id='inc_gehalt',
            start_date=date(2023, 1, 1),
            frequency='monthly',
            is_inflation_adjusted=True
        )
        CashFlowSource.objects.create(
            user=user, name='Partner Salary (Part-Time)',
            value=Decimal('1600.00'),
            is_income=True,
            category=category_objects['Salary'],
            template_id='inc_minijob',
            start_date=date(2023, 1, 1),
            frequency='monthly',
            is_inflation_adjusted=True
        )

        # 6. Create Expenses (CashFlowSource)
        CashFlowSource.objects.create(
            user=user, name='Cold Rent & Building Charges',
            value=Decimal('950.00'),
            is_income=False,
            category=category_objects['Rent'],
            template_id='exp_kaltmiete',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='Utilities & Heating',
            value=Decimal('280.00'),
            is_income=False,
            category=category_objects['Rent'],
            template_id='exp_nebenkosten',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='Groceries & Household',
            value=Decimal('650.00'),
            is_income=False,
            category=category_objects['Groceries'],
            template_id='exp_lebensmittel',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='ETF Savings Plan',
            value=Decimal('500.00'),
            is_income=False,
            category=category_objects['Investments'],
            template_id='exp_etf_sparplan',
            start_date=date(2023, 1, 1),
            frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name='Car Insurance',
            value=Decimal('480.00'),
            is_income=False,
            category=category_objects['Insurance'],
            template_id='exp_kfz_versicherung',
            start_date=date(2024, 1, 1),
            frequency='yearly'
        )
        CashFlowSource.objects.create(
            user=user, name='Personal Liability & Contents Insurance',
            value=Decimal('180.00'),
            is_income=False,
            category=category_objects['Insurance'],
            template_id='exp_haftpflicht',
            start_date=date(2024, 1, 1),
            frequency='yearly'
        )

        # 7. Create RealEstate with full fields + linked Loan
        re1 = RealEstate.objects.create(
            user=user,
            name='Condominium Munich (Rental)',
            property_value=Decimal('480000.00'),
            appreciation_rate=Decimal('2.5'),
            location='Munich - Schwabing',
            acquisition_date=date(2015, 3, 15),
            rental_income_monthly=Decimal('1450.00'),
            maintenance_costs_monthly=Decimal('180.00'),
            ancillary_costs_monthly=Decimal('80.00'),
            current_tenant='Maria Meier',
            construction_year=1998,
            living_space_sqm=Decimal('72.00'),
            current_maintenance_reserve=Decimal('8500.00'),
            monthly_maintenance_allocation=Decimal('200.00'),
            building_share_percent=Decimal('70.00'),
            depreciation_rate_percent=Decimal('2.00'),
            is_rental_property=True,
        )

        Loan.objects.create(
            user=user,
            real_estate=re1,
            name='Mortgage - Schwabing Condo',
            provider='Sparkasse Munich',
            loan_type='annuity',
            nominal_amount=Decimal('280000.00'),
            interest_rate=Decimal('1.85'),
            monthly_installment=Decimal('1050.00'),
            start_date=date(2015, 3, 1),
            end_date=date(2045, 3, 1),
            interest_lock_end=date(2025, 3, 1),
        )

        # Property components for re1
        PropertyComponent.objects.create(
            real_estate=re1,
            component_type='roof',
            name='Flat Roof (Bitumen Membrane)',
            installation_year=2015,
            expected_lifespan=30,
            estimated_cost=Decimal('22000.00'),
            condition='good',
            notes='Renewed at acquisition. Next inspection 2030.'
        )
        PropertyComponent.objects.create(
            real_estate=re1,
            component_type='heating',
            name='Gas Condensing Boiler',
            installation_year=2016,
            expected_lifespan=20,
            estimated_cost=Decimal('12000.00'),
            condition='good',
            notes='Annual maintenance contract with local service provider.'
        )
        PropertyComponent.objects.create(
            real_estate=re1,
            component_type='windows',
            name='Double-Glazed PVC Windows',
            installation_year=2010,
            expected_lifespan=25,
            estimated_cost=Decimal('9500.00'),
            condition='moderate',
            notes='Seals showing slight wear; plan replacement around 2035.'
        )
        PropertyComponent.objects.create(
            real_estate=re1,
            component_type='electrical',
            name='Main Electrical Panel',
            installation_year=1998,
            expected_lifespan=30,
            estimated_cost=Decimal('4500.00'),
            condition='moderate',
            notes='Original installation; check with electrician before 2028.'
        )

        # 8. Create Pensions
        Pension.objects.create(
            user=user,
            provider='German Pension Insurance (Demo)',
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
            provider='Company Pension (bAV)',
            pension_type='capital',
            current_value=Decimal('24000.00'),
            monthly_contribution=Decimal('150.00'),
            growth_rate=Decimal('3.50'),
            expected_payout_at_retirement=Decimal('280.00'),
            retirement_age=67,
            start_payout_date=date(2052, 6, 1)
        )

        # 9. Create OneTimeEvents
        today = date.today()
        OneTimeEvent.objects.create(
            user=user, name='Tax Refund',
            value=Decimal('1200.00'),
            date=date(today.year, 8, 15),
            description='Expected income tax refund'
        )
        OneTimeEvent.objects.create(
            user=user, name='Holiday Trip',
            value=Decimal('-2500.00'),
            date=date(today.year, 10, 10),
            description='Summer vacation (flights + hotel)'
        )

        self.stdout.write(self.style.SUCCESS('[OK] Successfully seeded database with comprehensive demo data.'))
