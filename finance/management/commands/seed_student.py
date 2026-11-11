from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import CustomUser, UserProfile, get_dashboard_config_for_situation
from finance.models import (
    Category, CashFlowSource, Asset, Loan, InsurancePolicy, AssetSnapshot
)


class Command(BaseCommand):
    help = "Seeds demo_student: Student with BAföG, Minijob, shared flat rent & KfW student loan"

    def handle(self, *args, **options):
        username = "student"
        user, _ = CustomUser.objects.get_or_create(
            username=username,
            defaults={'email': 'student@finanzplan.local', 'first_name': 'Tim', 'last_name': 'Neumann'}
        )
        user.set_password(username)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Tim Neumann"
        profile.household_situation = "student"
        profile.birth_date = date(2003, 6, 18)
        profile.retirement_age = 67
        profile.partner_name = ""
        profile.partner_birth_date = None
        profile.target_pension_payout = Decimal("2600.00")
        profile.inflation_rate = Decimal("2.00")
        profile.pension_increase = Decimal("1.50")
        profile.hide_wizard_on_start = True
        profile.dashboard_config = get_dashboard_config_for_situation("student")
        profile.save()

        CashFlowSource.objects.filter(user=user).delete()
        Asset.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()
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
        cat_freizeit = get_cat("leisure", "Freizeit und Medien", "#0dcaf0")

        # Income
        CashFlowSource.objects.create(
            user=user, name="BAföG Höchstsatz / Förderung", value=Decimal("812.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_bafoeg", owner_role="primary", end_date=date(2028, 9, 30)
        )
        CashFlowSource.objects.create(
            user=user, name="Werkstudent / Minijob IT-Support", value=Decimal("538.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_minijob", owner_role="primary", end_date=date(2028, 9, 30)
        )
        CashFlowSource.objects.create(
            user=user, name="Berufseinstieg Einstiegsgehalt (Prognose ab 2028)", value=Decimal("2650.00"),
            is_income=True, frequency="monthly", category=cat_gehalt,
            template_id="inc_gehalt", owner_role="primary", start_date=date(2028, 10, 1)
        )

        # Expenses
        CashFlowSource.objects.create(
            user=user, name="WG-Zimmer Warmmiete", value=Decimal("490.00"),
            is_income=False, frequency="monthly", category=cat_wohnen, template_id="exp_miete"
        )
        CashFlowSource.objects.create(
            user=user, name="Mensa & Lebensmittel", value=Decimal("290.00"),
            is_income=False, frequency="monthly", category=cat_essen, template_id="exp_lebensmittel"
        )
        CashFlowSource.objects.create(
            user=user, name="Semesterbeitrag / ÖPNV / Lernmittel", value=Decimal("110.00"),
            is_income=False, frequency="monthly", category=cat_freizeit, template_id="exp_handy_internet"
        )
        CashFlowSource.objects.create(
            user=user, name="Studentische Kranken- & Pflegeversicherung", value=Decimal("132.00"),
            is_income=False, frequency="monthly", category=cat_freizeit, template_id="exp_haftpflicht"
        )

        # Assets
        Asset.objects.create(
            user=user, name="Girokonto N26", asset_type="cash",
            value=Decimal("620.00"), monthly_savings_amount=Decimal("0.00"), growth_rate=Decimal("0.00")
        )
        Asset.objects.create(
            user=user, name="Tagesgeld Notgroschen", asset_type="overnight",
            value=Decimal("1500.00"), monthly_savings_amount=Decimal("50.00"),
            growth_rate=Decimal("2.50"), is_emergency_fund=True
        )

        # BAföG / KfW Loan starting repayment later
        Loan.objects.create(
            user=user, name="KfW Studienkredit / BAföG-Anteil",
            nominal_amount=Decimal("7500.00"),
            interest_rate=Decimal("4.20"), monthly_installment=Decimal("130.00"),
            start_date=date(2024, 10, 1), owner_role="primary"
        )

        # Insurances: Privathaftpflicht active, BU intentionally missing
        InsurancePolicy.objects.create(
            user=user, name="Privathaftpflicht Student", insurance_type="liability",
            provider="Getsafe", insured_person="primary", premium_amount=Decimal("4.10"),
            payment_frequency="monthly", coverage_lump_sum=Decimal("20000000.00"),
            include_in_cashflow=True, is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f"Seeded {username} (Student / Berufseinsteiger) successfully."))
