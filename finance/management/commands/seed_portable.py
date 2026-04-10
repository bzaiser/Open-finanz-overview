import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from finance.models import Category, CashFlowSource, Asset, OneTimeEvent, Pension, ImportBatch, PendingTransaction, RealEstate, Loan
from core.models import UserProfile
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with a complete, beautiful demo dataset for portable deployment'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING('Starting Ultra-Seed for Portable Deployment...'))

        # 1. Create Demo User
        username = 'demo'
        password = 'demo'
        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created user "{username}"'))
        else:
            self.stdout.write(self.style.WARNING(f'Resetting data for existing user "{username}"'))

        # 2. Setup Profile & Dashboard Design
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Max Mustermann"
        profile.currency = "EUR"
        profile.language = "de"
        profile.birth_date = datetime.date(1985, 5, 15)
        
        # Design Colors (Modern & Professional)
        profile.primary_color = "#0d6efd"
        profile.secondary_color = "#6c757d"
        profile.gradient_start = "#6610f2"
        profile.gradient_end = "#0d6efd"
        
        # Dashboard Config (Organized Grid)
        profile.dashboard_config = {
            "widgets": [
                {"id": "net_worth", "visible": True, "order": 1},
                {"id": "cash_flow_summary", "visible": True, "order": 2},
                {"id": "savings_rate", "visible": True, "order": 3},
                {"id": "import_status", "visible": True, "order": 4},
                {"id": "loan_summary", "visible": True, "order": 5},
                {"id": "pension_forecast", "visible": True, "order": 6}
            ]
        }
        profile.save()

        # 3. Clear existing data to avoid duplicates
        Category.objects.all().delete()
        CashFlowSource.objects.filter(user=user).delete()
        Asset.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()
        ImportBatch.objects.filter(user=user).delete()
        RealEstate.objects.filter(user=user).delete()
        Loan.objects.filter(user=user).delete()

        # 4. Create Categories with Colors
        categories_data = [
            ('Gehalt', 'salary', '#198754'),      # Green
            ('Wohnen', 'housing', '#dc3545'),     # Red
            ('Lebensmittel', 'food', '#ffc107'),   # Yellow
            ('Freizeit', 'leisure', '#0dcaf0'),   # Light Blue
            ('Investition', 'investment', '#6610f2'), # Purple
            ('Versicherung', 'insurance', '#fd7e14'), # Orange
            ('Auto', 'car', '#212529'),           # Dark
        ]
        categories = {}
        for name, slug, color in categories_data:
            cat = Category.objects.create(name=name, slug=slug, color=color)
            categories[slug] = cat

        # 5. Assets & Pensions
        Asset.objects.create(user=user, name="Girokonto", value=Decimal("2500.00"), growth_rate=0.0)
        Asset.objects.create(user=user, name="Tagesgeld", value=Decimal("15000.00"), growth_rate=2.5)
        Asset.objects.create(user=user, name="ETF Portfolio", value=Decimal("45000.00"), growth_rate=7.0)
        
        Pension.objects.create(
            user=user, provider="Gesetzliche Rente", current_value=0, 
            monthly_contribution=350, growth_rate=1.0, 
            expected_payout_at_retirement=1250.00,
            start_payout_date=datetime.date(2052, 1, 1)
        )

        # 6. Cash Flow (Income & Expenses)
        CashFlowSource.objects.create(
            user=user, name="Hautpberuf Gehalt", value=3200.00, is_income=True, 
            category=categories['salary'], frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name="Miete", value=1150.00, is_income=False, 
            category=categories['housing'], frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name="Lebensmittel", value=600.00, is_income=False, 
            category=categories['food'], frequency='monthly'
        )

        # 7. ONE-TIME EVENTS
        # today = datetime.date.today()
        # No events yet or optional

        # 8. BANK IMPORT DEMO DATA (Pending Transactions)
        # This allows users to test the "Review" page immediately
        batch = ImportBatch.objects.create(
            user=user, 
            filename="demo_kontoauszug.csv",
            is_applied=False
        )
        
        demo_txs = [
            {"date": timezone.now().date(), "desc": "REWE SAGT DANKE", "amt": -45.60, "cat": categories['food']},
            {"date": timezone.now().date(), "desc": "SHELL STATION", "amt": -75.00, "cat": categories['car']},
            {"date": timezone.now().date(), "desc": "NETFLIX.COM", "amt": -17.99, "cat": categories['leisure']},
            {"date": timezone.now().date(), "desc": "VATTENFALL STROM", "amt": -89.00, "cat": categories['housing']},
            {"date": timezone.now().date(), "desc": "ÜBERWEISUNG GEHALT", "amt": 3200.00, "cat": categories['salary']},
        ]
        
        for tx in demo_txs:
            PendingTransaction.objects.create(
                batch=batch,
                date=tx['date'],
                description=tx['desc'],
                amount=tx['amt'],
                is_income=(tx['amt'] > 0),
                category=tx['cat']
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded complete portable demo data for "{user.username}"'))
        self.stdout.write(self.style.HTTP_INFO('Login: demo / demo'))
