from django.test import TestCase
from django.urls import reverse
from .models import CustomUser, UserProfile


class ProfileThemeStudioTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="theme_tester", password="pw")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.client.force_login(self.user)

    def test_profile_post_with_theme_sync_cards_serializes_cleanly(self):
        resp = self.client.post(
            reverse("profile"),
            {
                "language": "de",
                "currency": "EUR",
                "retirement_age": 67,
                "partner_retirement_age": 67,
                "simulation_max_age": 95,
                "target_pension_payout": "2500.00",
                "inflation_rate": "2.00",
                "salary_increase": "1.50",
                "pension_increase": "1.00",
                "investment_return_offset": "0.00",
                "real_estate_growth_rate": "2.00",
                "backup_frequency": "never",
                "backup_max_keep": 5,
                "gradient_start": "#3b82f6",
                "gradient_end": "#f43f5e",
                "primary_color": "#3b82f6",
                "background_color": "#f4f6f9",
                "text_color": "#1e293b",
                "theme_mood": "dualtone",
                "theme_bg_mode": "auto",
                "theme_bg_custom": "#e2e8f0",
                "theme_sync_cards": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        dc = self.profile.dashboard_config
        self.assertEqual(dc["theme_studio"]["mood"], "dualtone")
        self.assertTrue(dc["theme_studio"]["sync_cards_and_charts"])
        self.assertIn("summary_layout", dc)
        self.assertIn("card_groups", dc)

