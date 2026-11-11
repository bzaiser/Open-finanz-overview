import datetime
import json
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CustomUser, UserProfile, get_dashboard_config_for_situation
from finance.models import Asset, CashFlowSource, InsurancePolicy, Pension
from finance.services import SimulationEngine
from finance.services_risk import calculate_protection_audit


class RiskAndInsuranceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="tester", password="TestPassword123!")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.household_situation = "family"
        self.profile.birth_date = datetime.date(1988, 5, 10)
        self.profile.partner_name = "Partner"
        self.profile.save()

        self.bank = Asset.objects.create(
            user=self.user,
            name="Girokonto",
            asset_type="cash",
            value=Decimal("10000.00"),
            growth_rate=Decimal("0.00"),
            is_emergency_fund=True,
        )
        self.salary_primary = CashFlowSource.objects.create(
            user=self.user,
            name="Gehalt Hauptperson",
            value=Decimal("3000.00"),
            is_income=True,
            frequency="monthly",
            template_id="inc_gehalt",
            owner_role="primary",
        )
        self.salary_partner = CashFlowSource.objects.create(
            user=self.user,
            name="Gehalt Partner",
            value=Decimal("1500.00"),
            is_income=True,
            frequency="monthly",
            template_id="inc_gehalt",
            owner_role="partner",
        )
        self.kindergeld = CashFlowSource.objects.create(
            user=self.user,
            name="Kindergeld",
            value=Decimal("255.00"),
            is_income=True,
            frequency="monthly",
            template_id="inc_kindergeld",
            owner_role="joint",
        )
        self.rent = CashFlowSource.objects.create(
            user=self.user,
            name="Miete",
            value=Decimal("2500.00"),
            is_income=False,
            frequency="monthly",
            template_id="exp_miete",
        )
        self.drv_primary = Pension.objects.create(
            user=self.user,
            provider="DRV Primary",
            pension_type="statutory",
            owner_role="primary",
            disability_pension_net=Decimal("1000.00"),
            expected_payout_at_retirement=Decimal("1600.00"),
            retirement_age=67,
        )

    def _next_month_str(self):
        today = timezone.now().date().replace(day=1)
        next_m = today + datetime.timedelta(days=32)
        return next_m.replace(day=1).strftime("%Y-%m-%d")

    def _month_after_str(self, months=3):
        today = timezone.now().date().replace(day=1)
        m = today.month - 1 + months
        y = today.year + m // 12
        m = m % 12 + 1
        return f"{y}-{m:02d}-01"

    def test_insurance_premium_prevents_double_counting(self):
        # Unlinked policy should reduce net cashflow
        InsurancePolicy.objects.create(
            user=self.user,
            name="BU Police",
            insurance_type="disability",
            insured_person="primary",
            premium_amount=Decimal("100.00"),
            payment_frequency="monthly",
            coverage_monthly_payout=Decimal("1200.00"),
            include_in_cashflow=True,
            is_active=True,
        )
        # Linked policy must NOT deduct premium twice
        InsurancePolicy.objects.create(
            user=self.user,
            name="Haftpflicht Linked",
            insurance_type="liability",
            insured_person="joint",
            premium_amount=Decimal("200.00"),
            payment_frequency="monthly",
            linked_cash_flow=self.rent,
            include_in_cashflow=True,
            is_active=True,
        )
        forecast = SimulationEngine(self.user, {"months": 6, "use_cache": False}).get_forecast()
        # Net income = 3000 + 1500 + 255 = 4755; expenses = 2500 + 100 (unlinked only) = 2600
        first_month = forecast[0]
        self.assertAlmostEqual(first_month["monthly_income"], 4755.0, places=1)
        self.assertAlmostEqual(first_month["monthly_expenses"], 2600.0, places=1)

    def test_job_loss_and_disability_and_partner_death_and_emergency_scenarios(self):
        start_str = self._next_month_str()

        # 1. Job Loss (primary): has_children=True -> 67% ALG I (2010); partner 1500 + kindergeld 255 stay -> 3765
        base_opts = {
            "months": 12,
            "inflation_rate": 0.0,
            "salary_increase": 0.0,
            "pension_increase": 0.0,
            "use_cache": False,
        }
        engine_job = SimulationEngine(
            self.user,
            {
                **base_opts,
                "risk_scenario": {
                    "type": "job_loss",
                    "person": "primary",
                    "start_date": start_str,
                    "duration_months": 6,
                    "pause_savings": False,
                    "emergency_amount": 0,
                },
            },
        )
        fc_job = engine_job.get_forecast()
        shock_month = next(pt for pt in fc_job if pt["date"].strftime("%Y-%m") == start_str[:7])
        self.assertAlmostEqual(shock_month["monthly_income"], 2010.0 + 1500.0 + 255.0, places=1)

        # 2. Disability with BU + 2 month waiting period
        InsurancePolicy.objects.create(
            user=self.user,
            name="Private BU",
            insurance_type="disability",
            insured_person="primary",
            premium_amount=Decimal("80.00"),
            payment_frequency="monthly",
            coverage_monthly_payout=Decimal("1200.00"),
            waiting_period_months=2,
            include_in_cashflow=False,
            is_active=True,
        )
        engine_dis = SimulationEngine(
            self.user,
            {
                **base_opts,
                "risk_scenario": {
                    "type": "disability",
                    "person": "primary",
                    "start_date": start_str,
                    "duration_months": 6,
                    "pause_savings": False,
                    "emergency_amount": 0,
                },
            },
        )
        fc_dis = engine_dis.get_forecast()
        m1_dis = next(pt for pt in fc_dis if pt["date"].strftime("%Y-%m") == start_str[:7])
        m3_key = self._month_after_str(3)[:7]
        m3_dis = next(pt for pt in fc_dis if pt["date"].strftime("%Y-%m") == m3_key)
        # Month 0 of shock: DRV (1000) + partner (1500) + kindergeld (255) = 2755 (waiting period prevents BU)
        self.assertAlmostEqual(m1_dis["monthly_income"], 2755.0, places=1)
        # Month 2+ of shock: DRV (1000) + BU (1200) + partner (1500) + kindergeld (255) = 3955
        self.assertAlmostEqual(m3_dis["monthly_income"], 3955.0, places=1)

        # 3. Partner death with Term Life lump sum
        InsurancePolicy.objects.create(
            user=self.user,
            name="Risikoleben Partner",
            insurance_type="term_life",
            insured_person="partner",
            premium_amount=Decimal("15.00"),
            payment_frequency="monthly",
            coverage_lump_sum=Decimal("50000.00"),
            include_in_cashflow=False,
            is_active=True,
        )
        fc_base = SimulationEngine(self.user, {**base_opts, "months": 6}).get_forecast()
        fc_death = SimulationEngine(
            self.user,
            {
                **base_opts,
                "months": 6,
                "risk_scenario": {
                    "type": "partner_death",
                    "person": "partner",
                    "start_date": start_str,
                    "duration_months": 12,
                    "pause_savings": False,
                    "emergency_amount": 0,
                },
            },
        ).get_forecast()
        m_death = next(pt for pt in fc_death if pt["date"].strftime("%Y-%m") == start_str[:7])
        m_base = next(pt for pt in fc_base if pt["date"].strftime("%Y-%m") == start_str[:7])
        self.assertAlmostEqual(m_death["monthly_income"], 3000.0 + 255.0, places=1)
        death_liq = m_death["accumulated_cash"] + m_death["asset_total"]
        base_liq = m_base["accumulated_cash"] + m_base["asset_total"]
        self.assertGreater(death_liq, base_liq + 40000.0)

        # 4. Emergency expense drops liquid wealth
        fc_emerg = SimulationEngine(
            self.user,
            {
                "months": 6,
                "use_cache": False,
                "risk_scenario": {
                    "type": "emergency_expense",
                    "person": "primary",
                    "start_date": start_str,
                    "duration_months": 1,
                    "pause_savings": False,
                    "emergency_amount": 15000,
                },
            },
        ).get_forecast()
        m_emerg = next(pt for pt in fc_emerg if pt["date"].strftime("%Y-%m") == start_str[:7])
        emerg_liq = m_emerg["accumulated_cash"] + m_emerg["asset_total"]
        self.assertLess(emerg_liq, base_liq - 14000.0)

    def test_protection_audit_and_insurance_crud_views(self):
        audit = calculate_protection_audit(self.user)
        self.assertIn("checklist", audit)
        self.assertEqual(audit["primary_earned_monthly"], 3000.0)
        self.assertEqual(audit["disability_covered_primary"], 1000.0)
        self.assertGreater(audit["disability_gap_primary"], 0.0)

        self.client.force_login(self.user)
        resp_add = self.client.post(
            reverse("finance:insurance_add"),
            {
                "name": "Haftpflicht Test",
                "insurance_type": "liability",
                "provider": "Allianz",
                "insured_person": "joint",
                "premium_amount": "8.50",
                "payment_frequency": "monthly",
                "coverage_lump_sum": "10000000",
                "coverage_monthly_payout": "0",
                "waiting_period_months": "0",
                "payout_duration_months": "0",
                "include_in_cashflow": "on",
                "is_active": "on",
            },
        )
        self.assertEqual(resp_add.status_code, 302)
        policy = InsurancePolicy.objects.get(user=self.user, name="Haftpflicht Test")
        self.assertEqual(policy.insurance_type, "liability")

        resp_page = self.client.get(reverse("finance:pension_plan") + "?tab=insurances")
        self.assertEqual(resp_page.status_code, 200)
        self.assertContains(resp_page, "Haftpflicht Test")
        self.assertContains(resp_page, "Risiko- & Notfall-Check")

        resp_del = self.client.post(reverse("finance:insurance_delete", args=[policy.id]))
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(InsurancePolicy.objects.filter(id=policy.id).exists())

    def test_wizard_saves_household_situation_and_owner_role(self):
        self.client.force_login(self.user)
        payload = {
            "household_type": "single",
            "household_situation": "single_parent",
            "p1_name": "Alleinerziehend Test",
            "p1_birth_date": "1990-01-01",
            "p1_retirement_age": 67,
            "target_monthly_payout": 2200,
            "incomes": [
                {
                    "template_id": "inc_gehalt",
                    "name": "Teilzeitgehalt",
                    "amount": 1900,
                    "frequency": "monthly",
                    "category_slug": "gehalt",
                    "owner_role": "primary",
                }
            ],
        }
        resp = self.client.post(
            reverse("finance:setup_wizard_save"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.household_situation, "single_parent")
        self.assertEqual(self.profile.dashboard_config, get_dashboard_config_for_situation("single_parent"))
        cf = CashFlowSource.objects.get(user=self.user, name="Teilzeitgehalt")
        self.assertEqual(cf.owner_role, "primary")


class TargetGroupSeedCommandsTests(TestCase):
    def test_seed_target_groups_and_render_pages(self):
        call_command("seed_target_groups")

        usernames = [
            "demo_geringverdiener",
            "demo_alleinerziehend",
            "demo_student",
            "demo_fruehrentner",
        ]
        for uname in usernames:
            user = CustomUser.objects.get(username=uname)
            self.client.force_login(user)

            r_dash = self.client.get(reverse("finance:dashboard"))
            self.assertEqual(r_dash.status_code, 200, f"Dashboard failed for {uname}")

            r_htmx = self.client.post(
                reverse("finance:dashboard"),
                {
                    "months": 24,
                    "risk_scenario_type": "job_loss",
                    "risk_scenario_person": "primary",
                    "risk_scenario_duration": 6,
                },
                HTTP_HX_REQUEST="true",
            )
            self.assertEqual(r_htmx.status_code, 200, f"Dashboard HTMX stresstest failed for {uname}")
            self.assertContains(r_htmx, "Stresstest aktiv")

            r_pens = self.client.get(reverse("finance:pension_plan"))
            self.assertEqual(r_pens.status_code, 200, f"Pension plan failed for {uname}")

            r_assets = self.client.get(reverse("finance:assets_overview"))
            self.assertEqual(r_assets.status_code, 200, f"Assets overview failed for {uname}")
