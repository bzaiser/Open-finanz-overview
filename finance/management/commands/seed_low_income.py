from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import CustomUser, UserProfile, get_dashboard_config_for_situation
from finance.models import (
    Category, CashFlowSource, Asset, Loan, Pension, InsurancePolicy, OneTimeEvent, AssetSnapshot
)


class Command(BaseCommand):
    help = "Seeds demo_geringverdiener: Low-income family with tight buffer, transfers & consumer loan"

    def handle(self, *args, **options):
        username = "demo_geringverdiener"
        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={'email': 'geringverdiener@finanzplan.local', 'first_name': 'Lukas', 'last_name': 'Weber'}
        )
        user.set_password("DemoUser2026!")
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Lukas & Jana Weber"
        profile.household_situation = "low_income"
        profile.birth_date = date(1990, 4, 12)
        profile.retirement_age = 67
        profile.partner_name = "Jana"
        profile.partner_birth_date = date(1992, 8, 20)
        profile.partner_retirement_age = 67
        profile.target_pension_payout = Decimal("2200.00")
        profile.inflation_rate = Decimal("2.00")
        profile.pension_increase = Decimal("1.50")
        profile.hide_wizard_on_start = True
        profile.dashboard_config = get_dashboard_config_for_situation("low_income")
        profile.save()

        CashFlowSource.objects.filter(user=user).delete()
        Asset.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()
        InsurancePolicy.objects.filter(user=user).delete()
        OneTimeEvent.objects.filter(user=user).delete()
        AssetSnapshot.objects.filter(user=user).delete()

        def get_cat(slug, name, color):
            cat = Category.objects.filter(slug=slug).first()
            if not cat:
                cat, _ = Category.objects.get_or_create(name=name, defaults={'slug': slug, 'color': color})
            return cat

        cat_gehalt = get_cat("gehalt", "Gehalt", "#198754")
        cat_wohnen = get_cat("wohnen", "Wohnen", "#0d6efd")
        cat_essen = get_cat("essen", "Essen", "#fd7e14")
        cat_vers = get_cat("versicherungen", "Versicherungen und Bank", "#20c997")
        cat_familie = get_cat("familie-kinder", "Familie & Kinder", "#ffc107")
        cat_kfz = get_cat("kfz", "KFZ", "#6c757d")
        cat_freizeit = get_cat("leisure", "Freizeit und Medien", "#0dcaf0")

        # Income
        CashFlowSource.objects.create(
            user=user, name="Lohn Lukas (Lagerlogistik)", value=Decimal("1850.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_gehalt", owner_role="primary", end_date=date(2057, 4, 30)
        )
        CashFlowSource.objects.create(
            user=user, name="Minijob Jana (Einzelhandel)", value=Decimal("538.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_minijob", owner_role="partner", end_date=date(2059, 8, 31)
        )
        CashFlowSource.objects.create(
            user=user, name="Kindergeld (1 Kind)", value=Decimal("255.00"),
            is_income=True, frequency="monthly", category=cat_familie,
            template_id="inc_kindergeld", owner_role="joint", end_date=date(2040, 12, 31)
        )
        CashFlowSource.objects.create(
            user=user, name="Wohngeld & Kinderzuschlag", value=Decimal("320.00"),
            is_income=True, frequency="monthly", category=cat_familie,
            template_id="inc_wohngeld", owner_role="joint"
        )

        # Expenses
        CashFlowSource.objects.create(
            user=user, name="Warmmiete 3-Zimmer-Wohnung", value=Decimal("980.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_miete"
        )
        CashFlowSource.objects.create(
            user=user, name="Strom & Internet", value=Decimal("145.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_nebenkosten"
        )
        CashFlowSource.objects.create(
            user=user, name="Lebensmittel & Drogerie", value=Decimal("680.00"),
            is_income=False, frequency="monthly", category=cat_essen, template_id="exp_lebensmittel"
        )
        CashFlowSource.objects.create(
            user=user, name="Kleinwagen & Sprit", value=Decimal("260.00"),
            is_income=False, frequency="monthly", category=cat_kfz, template_id="exp_tanken"
        )
        CashFlowSource.objects.create(
            user=user, name="Kita-Verpflegung & Schulbedarf", value=Decimal("140.00"),
            is_income=False, frequency="monthly", category=cat_familie, template_id="exp_kinderbetreuung"
        )
        CashFlowSource.objects.create(
            user=user, name="Mobilfunk & Freizeit", value=Decimal("120.00"),
            is_income=False, frequency="monthly", category=cat_freizeit, template_id="exp_handy_internet"
        )

        # Assets: small checking + small emergency reserve
        Asset.objects.create(
            user=user, name="Girokonto Sparkasse", asset_type="cash",
            value=Decimal("850.00"), monthly_savings_amount=Decimal("0.00"), growth_rate=Decimal("0.00")
        )
        Asset.objects.create(
            user=user, name="Tagesgeld Notgroschen", asset_type="overnight",
            value=Decimal("1900.00"), monthly_savings_amount=Decimal("75.00"),
            growth_rate=Decimal("2.50"), is_emergency_fund=True
        )

        # Consumer loan (Waschmaschine / Gebrauchtwagen)
        Loan.objects.create(
            user=user, name="Ratenkredit Gebrauchtwagen",
            nominal_amount=Decimal("4100.00"),
            interest_rate=Decimal("5.90"), monthly_installment=Decimal("185.00"),
            start_date=date(2024, 6, 1), owner_role="joint"
        )

        # Statutory pensions (with low EM pension)
        Pension.objects.create(
            user=user, provider="Deutsche Rentenversicherung (Lukas)",
            pension_type="statutory", owner_role="primary",
            pension_points=Decimal("14.20"), point_value=Decimal("40.79"),
            disability_pension_net=Decimal("820.00"), expected_payout_at_retirement=Decimal("1080.00"),
            retirement_age=67
        )
        Pension.objects.create(
            user=user, provider="Deutsche Rentenversicherung (Jana)",
            pension_type="statutory", owner_role="partner",
            pension_points=Decimal("8.50"), point_value=Decimal("40.79"),
            disability_pension_net=Decimal("520.00"), expected_payout_at_retirement=Decimal("690.00"),
            retirement_age=67
        )

        # Insurances: Haftpflicht present, BU and Term Life intentionally missing (gaps!)
        cf_hp = CashFlowSource.objects.create(
            user=user, name="Privathaftpflicht Familie", value=Decimal("6.50"),
            is_income=False, frequency="monthly", category=cat_vers, template_id="exp_haftpflicht"
        )
        InsurancePolicy.objects.create(
            user=user, name="Familien-Haftpflicht Basis", insurance_type="liability",
            provider="HUK24", insured_person="joint", premium_amount=Decimal("6.50"),
            payment_frequency="monthly", coverage_lump_sum=Decimal("10000000.00"),
            linked_cash_flow=cf_hp, include_in_cashflow=True, is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f"Seeded {username} (Geringverdiener-Familie) successfully."))
