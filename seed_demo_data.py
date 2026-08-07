import os
import sys
import django
from decimal import Decimal
from datetime import date

# Setup Django Environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finanzplan.settings")
django.setup()

from core.models import CustomUser, UserProfile
from finance.models import (
    Category, CashFlowSource, Asset, RealEstate, Loan, Pension, AssetSnapshot
)
from django.contrib.contenttypes.models import ContentType

def create_demo_user():
    username = "demo_familie"
    email = "demo@finanzplan.local"
    password = "DemoUser2026!"

    # Create or update user
    user, created = CustomUser.objects.get_or_create(
        username=username,
        defaults={'email': email, 'first_name': 'Markus', 'last_name': 'Mustermann'}
    )
    user.set_password(password)
    user.save()

    # User Profile (Mann 50 Jahre alt, verheiratet, Rente mit 67)
    # Geburtsjahr 1976 -> 2026 genau 50 Jahre alt
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.display_name = "Markus & Sandra Mustermann"
    profile.birth_date = date(1976, 5, 15) # Mann ist 50
    profile.retirement_age = 67
    profile.target_pension_payout = Decimal("4200.00") # Wunsch-Nettoeinkommen im Ruhestand
    profile.inflation_rate = Decimal("2.00")
    profile.pension_increase = Decimal("1.50")
    profile.save()

    print(f"✅ Benutzer '{username}' angelegt (Passwort: {password}).")

    # Clean existing demo data for clean rerun
    CashFlowSource.objects.filter(user=user).delete()
    Asset.objects.filter(user=user).delete()
    RealEstate.objects.filter(user=user).delete()
    Loan.objects.filter(user=user).delete()
    Pension.objects.filter(user=user).delete()
    AssetSnapshot.objects.filter(user=user).delete()

    # Get or create categories
    cat_gehalt, _ = Category.objects.get_or_create(name="Gehalt", defaults={'color': '#198754'})
    cat_wohnen, _ = Category.objects.get_or_create(name="Wohnen & Immo", defaults={'color': '#0d6efd'})
    cat_kinder, _ = Category.objects.get_or_create(name="Familie & Kinder", defaults={'color': '#ffc107'})
    cat_leben, _ = Category.objects.get_or_create(name="Lebenshaltung", defaults={'color': '#fd7e14'})
    cat_vorsorge, _ = Category.objects.get_or_create(name="Vorsorge & Sparen", defaults={'color': '#6f42c1'})
    cat_steuern, _ = Category.objects.get_or_create(name="Steuern & Abgaben", defaults={'color': '#dc3545'})

    # 1. Einnahmen (Familie)
    # Mann (50 Jahre, Besserverdiener): 5.200 € Netto / Monat
    CashFlowSource.objects.create(
        user=user,
        name="Gehalt Markus (Senior Manager)",
        value=Decimal("5200.00"),
        is_income=True,
        frequency="monthly",
        category=cat_gehalt,
        notes="Besserverdiener Vollzeit"
    )

    # Frau (48 Jahre, Teilzeit): 1.800 € Netto / Monat
    CashFlowSource.objects.create(
        user=user,
        name="Gehalt Sandra (Teilzeit)",
        value=Decimal("1800.00"),
        is_income=True,
        frequency="monthly",
        category=cat_gehalt,
        notes="Teilzeit 25h/Woche"
    )

    # Kindergeld für 2 Kinder: 250 € * 2 = 500 € / Monat
    CashFlowSource.objects.create(
        user=user,
        name="Kindergeld (2 Kinder)",
        value=Decimal("500.00"),
        is_income=True,
        frequency="monthly",
        category=cat_kinder,
        notes="Gültig bis Beendigung Studium/Ausbildung"
    )

    # 2. Regelmäßige Ausgaben
    # Nebenkosten & Instandhaltung Haus
    CashFlowSource.objects.create(
        user=user,
        name="Haus Nebenkosten & Grundsteuer",
        value=Decimal("550.00"),
        is_income=False,
        frequency="monthly",
        category=cat_wohnen
    )

    # Lebenshaltung, Einkäufe, Familie (4 Personen)
    CashFlowSource.objects.create(
        user=user,
        name="Haushalt & Lebensmittel",
        value=Decimal("1400.00"),
        is_income=False,
        frequency="monthly",
        category=cat_leben
    )

    # Auto, Versicherungen & Freizeit
    CashFlowSource.objects.create(
        user=user,
        name="Versicherungen & Mobilität",
        value=Decimal("650.00"),
        is_income=False,
        frequency="monthly",
        category=cat_leben
    )

    # Jährliche Einkommensteuer-Nachzahlung Rente / Nebenwerte
    CashFlowSource.objects.create(
        user=user,
        name="Einkommensteuer Nachzahlung",
        value=Decimal("1200.00"),
        is_income=False,
        frequency="yearly",
        start_date=date(2026, 7, 1),
        category=cat_steuern,
        notes="Jährliche Steuernachzahlung"
    )

    # 3. Immobilien & Darlehen
    # Eigenheim Wert 800.000 €
    house = RealEstate.objects.create(
        user=user,
        name="Einfamilienhaus (Eigenheim)",
        property_value=Decimal("800000.00"),
        appreciation_rate=Decimal("1.50"),
        location="München Umland",
        maintenance_costs_monthly=Decimal("250.00"),
        ancillary_costs_monthly=Decimal("300.00")
    )

    # Restschuld 450.000 € mit monatlicher Rate 2.100 €
    loan = Loan.objects.create(
        user=user,
        name="Immobiliendarlehen Haus",
        provider="Sparkasse",
        nominal_amount=Decimal("450000.00"),
        interest_rate=Decimal("2.25"),
        monthly_installment=Decimal("2100.00"),
        start_date=date(2018, 4, 1),
        end_date=date(2042, 4, 1),
        interest_lock_end=date(2033, 4, 1)
    )

    # 4. Bankkonten & Liquidität
    Asset.objects.create(
        user=user,
        name="Girokonto Sparkasse",
        value=Decimal("18500.00")
    )

    Asset.objects.create(
        user=user,
        name="Tagesgeld (Notgroschen)",
        value=Decimal("3500.00"),
        growth_rate=Decimal("2.50")
    )

    Asset.objects.create(
        user=user,
        name="ETF Depot (MSCI World / All World)",
        value=Decimal("125000.00"),
        growth_rate=Decimal("6.00")
    )

    # 5. Renten & Vorsorgeverträge
    ct_pension = ContentType.objects.get_for_model(Pension)

    # A) Gesetzliche Rente Markus (50 J., Besserverdiener -> bereits 58.5 EP gesammelt)
    p_markus = Pension.objects.create(
        user=user,
        provider="Deutsche Rentenversicherung (Markus)",
        pension_type="statutory",
        pension_points=Decimal("58.5000"),
        point_value=Decimal("39.32"),
        social_deduction_rate=Decimal("11.50"),
        expected_payout_at_retirement=Decimal("2037.00"), # Netto bei Renteneintritt
        retirement_age=67,
        start_payout_date=date(2043, 5, 15) # 2043 (67 Jahre alt)
    )

    # Historische Stichtage Markus (Entwicklung der Rentenpunkte)
    AssetSnapshot.objects.create(
        user=user, content_type=ct_pension, object_id=p_markus.id,
        date=date(2022, 12, 31), value=Decimal("1720.00"),
        pension_points=Decimal("51.2000"), point_value=Decimal("36.02"), expected_payout_net=Decimal("1630.00"),
        notes="Stichtagsmitteilung 2022"
    )
    AssetSnapshot.objects.create(
        user=user, content_type=ct_pension, object_id=p_markus.id,
        date=date(2024, 12, 31), value=Decimal("1910.00"),
        pension_points=Decimal("55.8000"), point_value=Decimal("39.32"), expected_payout_net=Decimal("1940.00"),
        notes="Stichtagsmitteilung 2024"
    )

    # B) Gesetzliche Rente Sandra (48 J., Teilzeit -> 24.2 EP gesammelt)
    p_sandra = Pension.objects.create(
        user=user,
        provider="Deutsche Rentenversicherung (Sandra)",
        pension_type="statutory",
        pension_points=Decimal("24.2000"),
        point_value=Decimal("39.32"),
        social_deduction_rate=Decimal("11.50"),
        expected_payout_at_retirement=Decimal("842.00"),
        retirement_age=67,
        start_payout_date=date(2045, 9, 1) # 2045 (67 Jahre alt)
    )

    # C) Private Altersvorsorge / Betriebsrente Markus (Kapital & Rente)
    p_bav = Pension.objects.create(
        user=user,
        provider="Allianz Direktversicherung (Markus bAV)",
        pension_type="capital",
        current_value=Decimal("68500.00"),
        monthly_contribution=Decimal("250.00"),
        growth_rate=Decimal("3.50"),
        expected_payout_at_retirement=Decimal("520.00"),
        retirement_age=67,
        start_payout_date=date(2043, 6, 1)
    )

    # D) Riester Rente Sandra
    p_riester = Pension.objects.create(
        user=user,
        provider="Union Investment Riester (Sandra)",
        pension_type="capital",
        current_value=Decimal("24800.00"),
        monthly_contribution=Decimal("160.00"),
        growth_rate=Decimal("3.00"),
        expected_payout_at_retirement=Decimal("190.00"),
        retirement_age=67,
        start_payout_date=date(2045, 10, 1)
    )

    print("🎉 Realistischer Demo-Datensatz für 'demo_familie' erfolgreich erstellt!")
    print("----------------------------------------------------------------------")
    print(f"👤 Benutzername: {username}")
    print(f"🔑 Passwort:    {password}")
    print("----------------------------------------------------------------------")
    print("📊 Profildaten:")
    print(" - Mann: 50 Jahre (Besserverdiener, Gehalt 5.200 € Netto, 58.5 Rentenpunkte)")
    print(" - Frau: 48 Jahre (Teilzeit, Gehalt 1.800 € Netto, 24.2 Rentenpunkte)")
    print(" - Haus: 800.000 € Immobilienwert | 450.000 € Restschuld (Rate 2.100 €/mtl.)")
    print(" - Private Vorsorge: Allianz bAV (68.500 €) + Riester (24.800 €) + ETF-Depot (125.000 €)")

if __name__ == "__main__":
    create_demo_user()
