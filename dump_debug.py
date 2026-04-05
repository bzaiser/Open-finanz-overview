import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finanzplaner.settings")
django.setup()

from finance.models import Pension
from core.models import CustomUser

u = CustomUser.objects.first()
print(f"User: {u.username}")
print(f"Profile pension_increase: {u.profile.pension_increase}")
for p in u.pensions.all():
    print(f"Pension {p.name}: expected={p.expected_payout_at_retirement}, start={p.start_payout_date}")
