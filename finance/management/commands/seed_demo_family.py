from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import date
from core.models import CustomUser, UserProfile
from finance.models import (
    Category, CashFlowSource, Asset, RealEstate, Loan, Pension, AssetSnapshot
)
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = "Seeds the database with a realistic demo family dataset based on wizard templates"

    def handle(self, *args, **options):
        username = "demo_familie"
        email = "demo@finanzplan.local"
        password = "DemoUser2026!"

        # 1. Create or update user
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': 'Markus', 'last_name': 'Mustermann'}
        )
        user.set_password(password)
        user.is_staff = True
        user.save()

        # 2. User Profile (Mann 50 Jahre, Geb. 1976; Frau Sandra 48 Jahre, Geb. 1978)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Markus & Sandra Mustermann"
        profile.birth_date = date(1976, 5, 15)  # Markus (50 J., Rente mit 67: Mai 2043)
        profile.retirement_age = 67
        profile.partner_name = "Sandra"
        profile.partner_birth_date = date(1978, 9, 1)  # Sandra (48 J., Rente mit 67: Sept 2045)
        profile.partner_retirement_age = 67
        profile.target_pension_payout = Decimal("4500.00")  # Wunsch-Nettoeinkommen im Ruhestand
        profile.inflation_rate = Decimal("2.00")
        profile.pension_increase = Decimal("1.50")
        profile.save()

        # 3. Clean existing demo data for clean rerun
        CashFlowSource.objects.filter(user=user).delete()
        Asset.objects.filter(user=user).delete()
        RealEstate.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()
        AssetSnapshot.objects.filter(user=user).delete()

        # 4. Standard Categories
        def get_cat(slug, name, color):
            cat = Category.objects.filter(slug=slug).first()
            if not cat:
                cat, _ = Category.objects.get_or_create(name=name, defaults={'slug': slug, 'color': color})
            return cat

        cat_gehalt = get_cat("gehalt", "Gehalt", "#11ff00")
        cat_wohnen = get_cat("wohnen", "Wohnen", "#0d6efd")
        cat_versicherungen = get_cat("versicherungen", "Versicherungen und Bank", "#20c997")
        cat_kfz = get_cat("kfz", "KFZ", "#6c757d")
        cat_essen = get_cat("essen", "Essen", "#fd7e14")
        cat_leisure = get_cat("leisure", "Freizeit und Medien", "#ffc107")
        cat_urlaub = get_cat("urlaub", "Urlaub", "#0dcaf0")
        cat_kleidung = get_cat("kleidung", "Kleidung", "#d63384")
        cat_investment = get_cat("investment", "Investment", "#6f42c1")
        cat_sparen = get_cat("sparen", "Sparen", "#198754")

        # 5. Einnahmen (mit Enddaten zur Rente / Ausbildung Kinder)
        # Markus (50 J., Senior Manager): 4.850 € Netto, endet mit 67 am 31.05.2043
        CashFlowSource.objects.create(
            user=user,
            name="Gehalt Markus (Senior Manager)",
            value=Decimal("4850.00"),
            is_income=True,
            frequency="monthly",
            category=cat_gehalt,
            template_id="inc_gehalt",
            end_date=date(2043, 5, 31),
            notes="Vollzeitgehalt Markus (endet bei Renteneintritt)"
        )

        # Sandra (48 J., Projektassistenz Teilzeit): 1.950 € Netto, endet mit 67 am 30.09.2045
        CashFlowSource.objects.create(
            user=user,
            name="Gehalt Sandra (Projektassistenz Teilzeit)",
            value=Decimal("1950.00"),
            is_income=True,
            frequency="monthly",
            category=cat_gehalt,
            template_id="inc_minijob",
            end_date=date(2045, 9, 30),
            notes="Teilzeitgehalt Sandra (endet bei Renteneintritt)"
        )

        # Kindergeld für 2 Kinder: 2x 255 € = 510 € Netto, befristet bis Ende Ausbildung
        CashFlowSource.objects.create(
            user=user,
            name="Kindergeld (2 Kinder)",
            value=Decimal("510.00"),
            is_income=True,
            frequency="monthly",
            category=cat_gehalt,
            template_id="inc_kindergeld",
            end_date=date(2032, 12, 31),
            notes="Kindergeld bis voraussichtliches Ausbildungsende"
        )

        # 6. Regelmäßige Ausgaben aus Vorlagenkatalog (nach Hausrate 2.350 € fast vollständig gebunden)
        # Wohnen & Haus
        CashFlowSource.objects.create(
            user=user,
            name="Nebenkosten / Hausgeld",
            value=Decimal("380.00"),
            is_income=False,
            frequency="monthly",
            category=cat_wohnen,
            template_id="exp_nebenkosten"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Gas / Fernwärme / Heizöl",
            value=Decimal("2640.00"),
            is_income=False,
            frequency="yearly",
            category=cat_wohnen,
            template_id="exp_heizung"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Strom",
            value=Decimal("1680.00"),
            is_income=False,
            frequency="yearly",
            category=cat_wohnen,
            template_id="exp_strom"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Grundsteuer",
            value=Decimal("600.00"),
            is_income=False,
            frequency="yearly",
            category=cat_wohnen,
            template_id="exp_grundsteuer"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Wohngebäudeversicherung",
            value=Decimal("720.00"),
            is_income=False,
            frequency="yearly",
            category=cat_wohnen,
            template_id="exp_wohngebaeude"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Instandhaltung & Reparaturen",
            value=Decimal("3000.00"),
            is_income=False,
            frequency="yearly",
            category=cat_wohnen,
            template_id="exp_instandhaltung"
        )

        # Versicherungen & Finanzen
        CashFlowSource.objects.create(
            user=user,
            name="Privathaftpflichtversicherung",
            value=Decimal("120.00"),
            is_income=False,
            frequency="yearly",
            category=cat_versicherungen,
            template_id="exp_haftpflicht"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Hausratversicherung",
            value=Decimal("240.00"),
            is_income=False,
            frequency="yearly",
            category=cat_versicherungen,
            template_id="exp_hausrat"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Berufsunfähigkeitsversicherung (BU Markus)",
            value=Decimal("110.00"),
            is_income=False,
            frequency="monthly",
            category=cat_versicherungen,
            template_id="exp_bu",
            end_date=date(2043, 5, 31),
            notes="Endet mit Renteneintritt von Markus"
        )
        CashFlowSource.objects.create(
            user=user,
            name="ETF- / Sparplan",
            value=Decimal("300.00"),
            is_income=False,
            frequency="monthly",
            category=cat_investment,
            template_id="exp_etf_sparplan",
            end_date=date(2043, 5, 31)
        )
        CashFlowSource.objects.create(
            user=user,
            name="Notgroschen / Sparkonto",
            value=Decimal("150.00"),
            is_income=False,
            frequency="monthly",
            category=cat_sparen,
            template_id="exp_notgroschen"
        )

        # KFZ & Mobilität (Familienwagen + Kleinwagen)
        CashFlowSource.objects.create(
            user=user,
            name="KFZ-Versicherung",
            value=Decimal("1440.00"),
            is_income=False,
            frequency="yearly",
            category=cat_kfz,
            template_id="exp_kfz_versicherung"
        )
        CashFlowSource.objects.create(
            user=user,
            name="KFZ-Steuer",
            value=Decimal("260.00"),
            is_income=False,
            frequency="yearly",
            category=cat_kfz,
            template_id="exp_kfz_steuer"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Kraftstoff / Laden",
            value=Decimal("3840.00"),
            is_income=False,
            frequency="yearly",
            category=cat_kfz,
            template_id="exp_kraftstoff"
        )
        CashFlowSource.objects.create(
            user=user,
            name="KFZ Wartung, TÜV & Reparatur",
            value=Decimal("1200.00"),
            is_income=False,
            frequency="yearly",
            category=cat_kfz,
            template_id="exp_kfz_wartung"
        )

        # Essen, Gesundheit & Alltag (4 Personen)
        CashFlowSource.objects.create(
            user=user,
            name="Lebensmittel & Drogerie",
            value=Decimal("1350.00"),
            is_income=False,
            frequency="monthly",
            category=cat_essen,
            template_id="exp_lebensmittel"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Kleidung & Schuhe",
            value=Decimal("3000.00"),
            is_income=False,
            frequency="yearly",
            category=cat_kleidung,
            template_id="exp_kleidung"
        )

        # Freizeit, Medien & Urlaub
        CashFlowSource.objects.create(
            user=user,
            name="Internet & Mobilfunk",
            value=Decimal("140.00"),
            is_income=False,
            frequency="monthly",
            category=cat_leisure,
            template_id="exp_internet"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Streaming & Abonnements",
            value=Decimal("780.00"),
            is_income=False,
            frequency="yearly",
            category=cat_leisure,
            template_id="exp_streaming"
        )
        CashFlowSource.objects.create(
            user=user,
            name="Urlaub & Reisen",
            value=Decimal("450.00"),
            is_income=False,
            frequency="monthly",
            category=cat_urlaub,
            template_id="exp_urlaub"
        )

        # 7. Immobilien & Darlehen
        # Eigenheim Wert 820.000 €
        RealEstate.objects.create(
            user=user,
            name="Einfamilienhaus (Eigenheim)",
            property_value=Decimal("820000.00"),
            appreciation_rate=Decimal("1.50"),
            location="München Umland",
            maintenance_costs_monthly=Decimal("250.00"),
            ancillary_costs_monthly=Decimal("350.00"),
            acquisition_date=date(2017, 3, 1)
        )

        # Darlehen 420.000 € mit monatlicher Rate 2.350 € (Restlaufzeit endet vor Rente)
        Loan.objects.create(
            user=user,
            name="Immobiliendarlehen Haus",
            provider="Sparkasse",
            nominal_amount=Decimal("420000.00"),
            interest_rate=Decimal("2.25"),
            monthly_installment=Decimal("2350.00"),
            start_date=date(2017, 3, 1),
            end_date=date(2039, 3, 1),
            interest_lock_end=date(2032, 3, 1)
        )

        # 8. Bankkonten & Vermögen
        Asset.objects.create(
            user=user,
            name="Girokonto Sparkasse",
            value=Decimal("14500.00")
        )
        Asset.objects.create(
            user=user,
            name="Tagesgeld (Notgroschen)",
            value=Decimal("30000.00"),
            growth_rate=Decimal("2.50")
        )
        Asset.objects.create(
            user=user,
            name="ETF Depot (MSCI World / All World)",
            value=Decimal("140000.00"),
            growth_rate=Decimal("6.00")
        )

        # 9. Rentenverträge (Aktueller Rentenwert: 40,79 €)
        CURRENT_RENTENWERT = Decimal("40.79")
        ct_pension = ContentType.objects.get_for_model(Pension)

        # A) Gesetzliche Rente Markus (50 J., Besserverdiener -> 48.5 EP gesammelt)
        # Netto heute: 48.5 * 40.79 * (1 - 0.115) = 1.750,80 €; Hochrechnung mit 67: 2.320 €
        p_markus = Pension.objects.create(
            user=user,
            provider="Deutsche Rentenversicherung (Markus)",
            pension_type="statutory",
            pension_points=Decimal("48.5000"),
            point_value=CURRENT_RENTENWERT,
            social_deduction_rate=Decimal("11.50"),
            expected_payout_at_retirement=Decimal("2320.00"),
            retirement_age=67,
            start_payout_date=date(2043, 5, 15)
        )

        # Historische Stichtage Markus
        AssetSnapshot.objects.create(
            user=user, content_type=ct_pension, object_id=p_markus.id,
            date=date(2023, 12, 31), value=Decimal("1650.00"),
            pension_points=Decimal("44.8000"), point_value=Decimal("37.60"),
            expected_payout_net=Decimal("1650.00"),
            notes="Stichtagsmitteilung 2023"
        )
        AssetSnapshot.objects.create(
            user=user, content_type=ct_pension, object_id=p_markus.id,
            date=date(2025, 12, 31), value=Decimal("1750.80"),
            pension_points=Decimal("48.5000"), point_value=CURRENT_RENTENWERT,
            expected_payout_net=Decimal("1750.80"),
            notes="Stichtagsmitteilung 2025"
        )

        # B) Gesetzliche Rente Sandra (48 J., vor Kindern Vollzeit 13 EP + 6 Kindererziehungs-EP + Teilzeit = 32.0 EP)
        # Netto heute: 32.0 * 40.79 * (1 - 0.115) = 1.155,10 €; Hochrechnung mit 67: 1.510 €
        p_sandra = Pension.objects.create(
            user=user,
            provider="Deutsche Rentenversicherung (Sandra)",
            pension_type="statutory",
            pension_points=Decimal("32.0000"),
            point_value=CURRENT_RENTENWERT,
            social_deduction_rate=Decimal("11.50"),
            expected_payout_at_retirement=Decimal("1510.00"),
            retirement_age=67,
            start_payout_date=date(2045, 9, 1)
        )
        AssetSnapshot.objects.create(
            user=user, content_type=ct_pension, object_id=p_sandra.id,
            date=date(2025, 12, 31), value=Decimal("1155.10"),
            pension_points=Decimal("32.0000"), point_value=CURRENT_RENTENWERT,
            expected_payout_net=Decimal("1155.10"),
            notes="Stichtagsmitteilung 2025"
        )

        # C) Private Altersvorsorge / Betriebsrente Markus (bAV)
        # Beiträge enden mit 67 (31.05.2043), Auszahlung startet 01.06.2043
        Pension.objects.create(
            user=user,
            provider="Allianz Direktversicherung (Markus bAV)",
            pension_type="capital",
            current_value=Decimal("72000.00"),
            monthly_contribution=Decimal("250.00"),
            growth_rate=Decimal("3.50"),
            expected_payout_at_retirement=Decimal("540.00"),
            retirement_age=67,
            contribution_end_date=date(2043, 5, 31),
            start_payout_date=date(2043, 6, 1)
        )

        # D) Riester Rente Sandra
        # Beiträge enden mit 67 (30.09.2045), Auszahlung startet 01.10.2045
        Pension.objects.create(
            user=user,
            provider="Union Investment Riester (Sandra)",
            pension_type="capital",
            current_value=Decimal("28500.00"),
            monthly_contribution=Decimal("160.00"),
            growth_rate=Decimal("3.00"),
            expected_payout_at_retirement=Decimal("210.00"),
            retirement_age=67,
            contribution_end_date=date(2045, 9, 30),
            start_payout_date=date(2045, 10, 1)
        )

        self.stdout.write(self.style.SUCCESS("[OK] Realistischer Demo-Familien-Datensatz erfolgreich angelegt!"))
        self.stdout.write(f"Benutzername: {username}")
        self.stdout.write(f"Passwort:    {password}")
