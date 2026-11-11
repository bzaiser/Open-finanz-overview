from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import CustomUser, UserProfile, get_dashboard_config_for_situation
from finance.models import (
    Category, CashFlowSource, Asset, Pension, InsurancePolicy, AssetSnapshot
)


class Command(BaseCommand):
    help = "Seeds demo_fruehrentner: Early retiree / reduced earning capacity pension & healthcare gap focus"

    def handle(self, *args, **options):
        username = "rentner"
        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={'email': 'fruehrentner@finanzplan.local', 'first_name': 'Sabine', 'last_name': 'Hoffmann'}
        )
        user.set_password(username)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Sabine Hoffmann"
        profile.household_situation = "early_retiree"
        profile.birth_date = date(1964, 2, 22)
        profile.retirement_age = 63
        profile.partner_name = ""
        profile.partner_birth_date = None
        profile.target_pension_payout = Decimal("2100.00")
        profile.inflation_rate = Decimal("2.20")
        profile.pension_increase = Decimal("1.50")
        profile.hide_wizard_on_start = True
        profile.dashboard_config = get_dashboard_config_for_situation("early_retiree")
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
        cat_health = get_cat("health", "Gesundheit", "#e83e8c")
        cat_vers = get_cat("versicherungen", "Versicherungen und Bank", "#20c997")

        # Income: EM-Rente / Vorgezogene Altersrente + kleiner Minijob-Hinzuverdienst
        CashFlowSource.objects.create(
            user=user, name="Hinzuverdienst Minijob (Büro)", value=Decimal("450.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_minijob", owner_role="primary", end_date=date(2031, 2, 28)
        )

        # Expenses
        CashFlowSource.objects.create(
            user=user, name="Miete 2-Zimmer barrierearm", value=Decimal("780.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_miete"
        )
        CashFlowSource.objects.create(
            user=user, name="Lebensmittel & Haushalt", value=Decimal("420.00"),
            is_income=False, frequency="monthly", category=cat_essen, template_id="exp_lebensmittel"
        )
        CashFlowSource.objects.create(
            user=user, name="Medikamente & Zuzahlungen Gesundheit", value=Decimal("95.00"),
            is_income=False, frequency="monthly", category=cat_health, template_id="exp_apotheke"
        )
        CashFlowSource.objects.create(
            user=user, name="Strom, Telefon & Deutschlandticket", value=Decimal("135.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_handy_internet"
        )

        # Assets: Reserve + kleine bAV / Sparbuch
        Asset.objects.create(
            user=user, name="Girokonto Postbank", asset_type="cash",
            value=Decimal("2400.00"), monthly_savings_amount=Decimal("0.00"), growth_rate=Decimal("0.00")
        )
        Asset.objects.create(
            user=user, name="Tagesgeld Gesundheit & Notfallreserve", asset_type="overnight",
            value=Decimal("11500.00"), monthly_savings_amount=Decimal("50.00"),
            growth_rate=Decimal("2.50"), is_emergency_fund=True
        )

        # Pensions: Already in payout!
        Pension.objects.create(
            user=user, provider="DRV Vorgezogene Rente (mit Abschlag)",
            pension_type="statutory", owner_role="primary",
            pension_points=Decimal("36.50"), point_value=Decimal("40.79"),
            gross_payout_amount=Decimal("1488.84"), social_deduction_rate=Decimal("11.50"),
            disability_pension_net=Decimal("1280.00"),
            expected_payout_at_retirement=Decimal("1317.62"),
            retirement_age=63, start_payout_date=date(2025, 1, 1)
        )
        Pension.objects.create(
            user=user, provider="Kleine Betriebsrente (VBL / bAV)",
            pension_type="occupational_fund", payout_type="lifelong_annuity",
            owner_role="primary", current_value=Decimal("28000.00"),
            expected_payout_at_retirement=Decimal("215.00"),
            retirement_age=63, start_payout_date=date(2026, 1, 1)
        )

        # Insurances: Privathaftpflicht + Pflegezusatzversicherung
        InsurancePolicy.objects.create(
            user=user, name="Privathaftpflicht Senioren", insurance_type="liability",
            provider="VHV", insured_person="primary", premium_amount=Decimal("5.90"),
            payment_frequency="monthly", coverage_lump_sum=Decimal("10000000.00"),
            include_in_cashflow=True, is_active=True
        )
        InsurancePolicy.objects.create(
            user=user, name="Pflegetagegeld Zusatzversicherung", insurance_type="health_addon",
            provider="Allianz", insured_person="primary", premium_amount=Decimal("42.00"),
            payment_frequency="monthly", coverage_monthly_payout=Decimal("900.00"),
            include_in_cashflow=True, is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f"Seeded {username} (Frührentner / Erwerbsminderung) successfully."))
