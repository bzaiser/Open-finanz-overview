import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from finance.models import Category, CashFlowSource, Asset, OneTimeEvent, Pension
from core.models import UserProfile, Theme
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with real-life example data'

    def handle(self, *args, **kwargs):
        # 1. Create a default theme if none exists
        theme, _ = Theme.objects.get_or_create(
            name="Professional Blue",
            defaults={
                'primary_color': '#0d6efd',
                'secondary_color': '#6c757d',
                'background_color': '#f8f9fa',
                'text_color': '#212529',
                'sidebar_bg_color': '#ffffff',
            }
        )

        # 2. Get or create a test user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
            self.stdout.write(self.style.SUCCESS(f'Created superuser "admin" with password "adminpass"'))

        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created:
            profile.theme = theme
            profile.birth_date = datetime.date(1985, 5, 15)
            profile.inflation_rate = 2.0
            profile.salary_increase = 1.5
            profile.investment_return_offset = 0.0
            profile.save()

        # 3. Create Categories
        categories_data = [
            ('Salary', 'salary', '#198754'),
            ('Housing', 'housing', '#dc3545'),
            ('Food', 'food', '#ffc107'),
            ('Leisure', 'leisure', '#0dcaf0'),
            ('Investment', 'investment', '#6610f2'),
            ('Insurance', 'insurance', '#fd7e14'),
        ]
        categories = {}
        for name, slug, color in categories_data:
            cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'color': color})
            categories[slug] = cat

        # 4. Clear existing data for this user to avoid duplicates if run multiple times
        CashFlowSource.objects.filter(user=user).delete()
        Asset.objects.filter(user=user).delete()
        OneTimeEvent.objects.filter(user=user).delete()
        Pension.objects.filter(user=user).delete()

        # 5. Add Cash Flow Sources (Income & Expenses)
        # Incomes
        CashFlowSource.objects.create(
            user=user, name="Main Salary", value=3500.00, is_income=True, 
            category=categories['salary'], frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name="Bonus", value=5000.00, is_income=True, 
            category=categories['salary'], frequency='yearly'
        )
        
        # Expenses
        CashFlowSource.objects.create(
            user=user, name="Rent", value=1200.00, is_income=False, 
            category=categories['housing'], frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name="Groceries", value=450.00, is_income=False, 
            category=categories['food'], frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name="Health Insurance", value=350.00, is_income=False, 
            category=categories['insurance'], frequency='monthly'
        )
        CashFlowSource.objects.create(
            user=user, name="Car Insurance", value=600.00, is_income=False, 
            category=categories['insurance'], frequency='yearly'
        )
        CashFlowSource.objects.create(
            user=user, name="Gym", value=45.00, is_income=False, 
            category=categories['leisure'], frequency='monthly'
        )

        # 6. Add Assets
        Asset.objects.create(user=user, name="Savings Account", value=15000.00, growth_rate=1.5)
        Asset.objects.create(user=user, name="Stock Portfolio (ETF)", value=45000.00, growth_rate=7.0)
        Asset.objects.create(user=user, name="Crypto", value=2500.00, growth_rate=15.0)

        # 7. Add Pensions
        Pension.objects.create(
            user=user, provider="State Pension", current_value=0.00, 
            monthly_contribution=350.00, growth_rate=1.0, 
            expected_payout_at_retirement=1200.00,
            start_payout_date=datetime.date(2052, 1, 1)
        )
        Pension.objects.create(
            user=user, provider="Company Pension (Allianz)", current_value=12000.00, 
            monthly_contribution=100.00, growth_rate=3.5, 
            expected_payout_at_retirement=450.00,
            start_payout_date=datetime.date(2052, 1, 1)
        )

        # 8. Add One-Time Events
        today = datetime.date.today()
        OneTimeEvent.objects.create(
            user=user, name="New Car Purchase", value=-25000.00, 
            date=today + datetime.timedelta(days=365*2),
            description="Planned upgrade for a family car"
        )
        OneTimeEvent.objects.create(
            user=user, name="Inheritance", value=50000.00, 
            date=today + datetime.timedelta(days=365*5),
            description="Estimated inheritance"
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully populated data for user "{user.username}"'))
