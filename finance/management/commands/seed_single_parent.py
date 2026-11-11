from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import CustomUser, UserProfile, get_dashboard_config_for_situation
from finance.models import (
    Category, CashFlowSource, Asset, Pension, InsurancePolicy, AssetSnapshot
)


class Command(BaseCommand):
    help = "Seeds demo_alleinerziehend: Single parent part-time with childcare costs, maintenance & BU/Term Life"

    def handle(self, *args, **options):
        username = "demo_alleinerziehend"
        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={'email': 'alleinerziehend@finanzplan.local', 'first_name': 'Anna', 'last_name': 'Keller'}
        )
        user.set_password("DemoUser2026!")
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Anna Keller"
        profile.household_situation = "single_parent"
        profile.birth_date = date(1989, 10, 5)
        profile.retirement_age = 67
        profile.partner_name = ""
        profile.partner_birth_date = None
        profile.target_pension_payout = Decimal("2400.00")
        profile.inflation_rate = Decimal("2.00")
        profile.pension_increase = Decimal("1.50")
        profile.hide_wizard_on_start = True
        profile.dashboard_config = get_dashboard_config_for_situation("single_parent")
        profile.save()

        CashFlowSource.objects.filter(user=user).delete()
        Asset.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()
        InsurancePolicy.objects.filter(user=user).delete()
        AssetSnapshot.objects.filter(user=user).delete()

        def get_cat(slug, name, color):
            cat = Category.objects.filter(slug=slug).first()
            if not cat:
                cat, _ = Category.objects.get_or_create(name=name, defaults={'slug': slug, 'color': color})
            return cat

        cat_gehalt = get_cat("gehalt", "Gehalt", "#198754")
        cat_wohnen = get_cat("wohnen", "Wohnen", "#0d6efd")
        cat_essen = get_cat("essen", "Essen", "#fd7e14")
        cat_familie = get_cat("familie-kinder", "Familie & Kinder", "#ffc107")
        cat_vers = get_cat("versicherungen", "Versicherungen und Bank", "#20c997")

        # Income
        CashFlowSource.objects.create(
            user=user, name="Teilzeitgehalt Anna (30 Std.)", value=Decimal("2150.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_gehalt", owner_role="primary", end_date=date(2056, 10, 31)
        )
        CashFlowSource.objects.create(
            user=user, name="Kindergeld (2 Kinder)", value=Decimal("510.00"),
            is_income=True, frequency="monthly", category=cat_familie,
            template_id="inc_kindergeld", owner_role="joint", end_date=date(2039, 12, 31)
        )
        CashFlowSource.objects.create(
            user=user, name="Unterhaltsvorschuss / Unterhalt", value=Decimal("420.00"),
            is_income=True, frequency="monthly", category=cat_familie,
            template_id="inc_unterhalt", owner_role="joint", end_date=date(2037, 12, 31)
        )

        # Expenses
        CashFlowSource.objects.create(
            user=user, name="Miete 3-Zimmer inkl. Heizung", value=Decimal("1050.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_miete"
        )
        CashFlowSource.objects.create(
            user=user, name="Kita & Hortbetreuung", value=Decimal("290.00"),
            is_income=False, frequency="monthly", category=cat_familie, template_id="exp_kinderbetreuung"
        )
        CashFlowSource.objects.create(
            user=user, name="Lebensmittel & Haushalt", value=Decimal("590.00"),
            is_income=False, frequency="monthly", category=cat_essen, template_id="exp_lebensmittel"
        )
        CashFlowSource.objects.create(
            user=user, name="ÖPNV Deutschlandticket + Handy", value=Decimal("95.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_handy_internet"
        )

        # Assets
        Asset.objects.create(
            user=user, name="Girokonto DKB", asset_type="cash",
            value=Decimal("1100.00"), monthly_savings_amount=Decimal("0.00"), growth_rate=Decimal("0.00")
        )
        Asset.objects.create(
            user=user, name="Tagesgeld Notreserve Kinder", asset_type="overnight",
            value=Decimal("4200.00"), monthly_savings_amount=Decimal("100.00"),
            growth_rate=Decimal("2.80"), is_emergency_fund=True
        )
        Asset.objects.create(
            user=user, name="Kinder-ETF Sparplan (MSCI World)", asset_type="depot",
            value=Decimal("2800.00"), monthly_savings_amount=Decimal("50.00"),
            growth_rate=Decimal("6.50")
        )

        # Pension
        Pension.objects.create(
            user=user, provider="Deutsche Rentenversicherung (Anna)",
            pension_type="statutory", owner_role="primary",
            pension_points=Decimal("19.80"), point_value=Decimal("40.79"),
            disability_pension_net=Decimal("1050.00"), expected_payout_at_retirement=Decimal("1340.00"),
            retirement_age=67
        )

        # Insurances: Haftpflicht + Term Life covered, BU intentionally missing/small to show audit details
        InsurancePolicy.objects.create(
            user=user, name="Privathaftpflicht Single mit Kindern", insurance_type="liability",
            provider="CosmosDirekt", insured_person="joint", premium_amount=Decimal("5.20"),
            payment_frequency="monthly", coverage_lump_sum=Decimal("15000000.00"),
            include_in_cashflow=True, is_active=True
        )
        cf_rlv = CashFlowSource.objects.create(
            user=user, name="Risikolebensversicherung Anna", value=Decimal("14.00"),
            is_income=False, frequency="monthly", category=cat_vers, template_id="exp_risikoleben"
        )
        InsurancePolicy.objects.create(
            user=user, name="Risikoleben Absicherung Kinder", insurance_type="term_life",
            provider="Hannoversche", insured_person="primary", premium_amount=Decimal("14.00"),
            payment_frequency="monthly", coverage_lump_sum=Decimal("150000.00"),
            linked_cash_flow=cf_rlv, include_in_cashflow=True, is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f"Seeded {username} (Alleinerziehend) successfully."))
