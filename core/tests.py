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

    def test_get_contrast_text_uses_perceptual_luminance(self):
        from .theme_engine import get_contrast_text
        self.assertEqual(get_contrast_text("#0d6efd"), "#ffffff")
        self.assertEqual(get_contrast_text("#198754"), "#ffffff")
        self.assertEqual(get_contrast_text("#dc3545"), "#ffffff")
        self.assertEqual(get_contrast_text("#ffc107"), "#1e293b")
        self.assertEqual(get_contrast_text("#A5D5C1"), "#1e293b")
        self.assertEqual(get_contrast_text("#ffffff"), "#1e293b")

    def test_kpi_2_extensions_and_mood_svg_mapping(self):
        from .theme_engine import get_profile_theme_studio_settings
        from finance.services_kpi import build_svg_sparkline, build_segmented_progress

        resp = self.client.post(
            reverse("profile"),
            {
                "language": "de",
                "currency": "EUR",
                "retirement_age": 67,
                "partner_retirement_age": 67,
                "simulation_max_age": 95,
                "target_pension_payout": "3000.00",
                "inflation_rate": "2.00",
                "salary_increase": "1.50",
                "pension_increase": "1.00",
                "investment_return_offset": "0.00",
                "real_estate_growth_rate": "2.00",
                "backup_frequency": "never",
                "backup_max_keep": 5,
                "gradient_start": "#10b981",
                "gradient_end": "#6366f1",
                "primary_color": "#10b981",
                "background_color": "#0f172a",
                "text_color": "#f8fafc",
                "theme_mood": "serioes",
                "theme_bg_mode": "dark",
                "theme_card_surface": "auto",
                "theme_bg_svg_mode": "auto",
                "kpi_ext_present": "1",
                "kpi_sparklines": "on",
                "kpi_progress_bars": "on",
                "kpi_watermarks": "",
                "kpi_spotlight": "on",
                "kpi_click_navigation": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        ts = get_profile_theme_studio_settings(self.profile)
        self.assertEqual(ts["resolved_card_surface"], "glass")
        self.assertEqual(ts["resolved_bg_svg"], "grid")
        self.assertTrue(ts["kpi_sparklines"])
        self.assertTrue(ts["kpi_progress_bars"])
        self.assertFalse(ts["kpi_watermarks"])
        self.assertTrue(ts["kpi_spotlight"])
        self.assertTrue(ts["kpi_click_navigation"])

        sp = build_svg_sparkline([100, 120, 115, 160, 200])
        self.assertIsNotNone(sp)
        self.assertTrue(sp["line"].startswith("M0.0,"))
        self.assertTrue(sp["area"].endswith("Z"))

        prog = build_segmented_progress(2100, 3000, marker_pct=80, label="70%")
        self.assertEqual(prog["pct"], 70)
        self.assertEqual(prog["active_count"], 7)
        self.assertEqual(sum(1 for s in prog["segments"] if s), 7)



