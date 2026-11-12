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
        self.assertContains(resp_page, "Vorsorge & Rentenbasis")
        self.assertContains(resp_page, "Absicherungs-Check")
        self.assertContains(resp_page, "Basis-Schutz Quote")

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
        resp_seed = self.client.post(reverse("load_demo_family"), follow=True)
        self.assertEqual(resp_seed.status_code, 200)
        for uname in ("demo_familie", "gering", "allein", "student", "rentner"):
            self.assertContains(resp_seed, uname)
            u = CustomUser.objects.get(username=uname)
            self.assertTrue(u.check_password(uname), f"Password mismatch for {uname}")

        usernames = [
            "gering",
            "allein",
            "student",
            "rentner",
        ]
        for uname in usernames:
            user = CustomUser.objects.get(username=uname)
            self.client.force_login(user)

            r_dash = self.client.get(reverse("finance:dashboard"))
            self.assertEqual(r_dash.status_code, 200, f"Dashboard failed for {uname}")
            self.assertContains(r_dash, "--app-table-header-bg: #0d6efd;")

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

            r_assets = self.client.get(reverse("finance:assets_overview"), HTTP_ACCEPT_LANGUAGE="de")
            self.assertEqual(r_assets.status_code, 200, f"Assets overview failed for {uname}")
            self.assertContains(r_assets, "4 %-Entnahmeregel (SWR)")
            self.assertContains(r_assets, "Jährliche sichere Entnahme (4 %)")
            self.assertContains(r_assets, "Erwartete Rendite (% p.a.)")
            self.assertContains(r_assets, "ETF-Sparplan & Zinseszins Rechner")
            self.assertContains(r_assets, "Tagesgeld / Geldmarkt")


class InsurancePolicyAdminTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_superuser(
            username="admin_u", email="a@example.com", password="AdminPassword123!"
        )
        self.other_user = CustomUser.objects.create_user(
            username="other_u", email="o@example.com", password="OtherPassword123!"
        )
        self.admin_cf_free = CashFlowSource.objects.create(
            user=self.admin_user, name="Haftpflicht Frei", value=Decimal("9.90"), is_income=False, frequency="monthly"
        )
        self.admin_cf_linked = CashFlowSource.objects.create(
            user=self.admin_user, name="BU Verknüpft", value=Decimal("55.00"), is_income=False, frequency="monthly"
        )
        self.admin_cf_income = CashFlowSource.objects.create(
            user=self.admin_user, name="Admin Gehalt", value=Decimal("3000.00"), is_income=True, frequency="monthly"
        )
        self.other_cf_free = CashFlowSource.objects.create(
            user=self.other_user, name="Other Hausrat", value=Decimal("14.00"), is_income=False, frequency="monthly"
        )
        self.existing_policy = InsurancePolicy.objects.create(
            user=self.admin_user,
            name="Bestehende BU",
            insurance_type="disability",
            premium_amount=Decimal("55.00"),
            linked_cash_flow=self.admin_cf_linked,
        )

    def test_admin_add_defaults_user_filters_cashflows_and_disables_linked(self):
        self.client.force_login(self.admin_user)
        add_url = reverse("admin:finance_insurancepolicy_add")
        resp = self.client.get(add_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        # Currently logged-in user selected by default
        self.assertIn(f'<option value="{self.admin_user.pk}" selected', html)
        # Only selected user's expense cashflows in <select> options initially
        self.assertIn(f'<option value="{self.admin_cf_free.pk}">', html)
        self.assertNotIn(f'<option value="{self.other_cf_free.pk}"', html)
        self.assertNotIn(f'<option value="{self.admin_cf_income.pk}"', html)
        # Already linked cashflow rendered disabled and not selectable
        self.assertIn(f'<option value="{self.admin_cf_linked.pk}" disabled="disabled">', html)
        self.assertIn("admin_insurance_policy.js", html)
        self.assertIn("data-cashflows", html)

        # Trying to POST with already-linked cashflow is rejected
        resp_post_dup = self.client.post(
            add_url,
            {
                "user": self.admin_user.pk,
                "name": "Zweite BU",
                "insurance_type": "disability",
                "insured_person": "primary",
                "premium_amount": "55.00",
                "payment_frequency": "monthly",
                "linked_cash_flow": self.admin_cf_linked.pk,
                "waiting_period_months": "0",
            },
        )
        self.assertEqual(resp_post_dup.status_code, 200)
        self.assertContains(resp_post_dup, "bereits mit")

        # Switching user to other_user and selecting other_cf_free succeeds
        resp_post_other = self.client.post(
            add_url,
            {
                "user": self.other_user.pk,
                "name": "Hausrat Other",
                "insurance_type": "household",
                "insured_person": "primary",
                "premium_amount": "14.00",
                "payment_frequency": "monthly",
                "linked_cash_flow": self.other_cf_free.pk,
                "waiting_period_months": "0",
            },
        )
        self.assertEqual(resp_post_other.status_code, 302)
        self.assertTrue(
            InsurancePolicy.objects.filter(
                user=self.other_user, name="Hausrat Other", linked_cash_flow=self.other_cf_free
            ).exists()
        )

    def test_admin_change_keeps_own_linked_cashflow_selectable(self):
        self.client.force_login(self.admin_user)
        change_url = reverse("admin:finance_insurancepolicy_change", args=[self.existing_policy.pk])
        resp = self.client.get(change_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn(f'<option value="{self.admin_cf_linked.pk}" selected>', html)

    def test_admin_changelists_render_german_translations(self):
        from django.contrib.contenttypes.models import ContentType
        from finance.models import Asset, AssetSnapshot, PropertyComponent, RealEstate

        re_obj = RealEstate.objects.create(
            user=self.admin_user, name="Haus Test", property_value=Decimal("250000.00")
        )
        PropertyComponent.objects.create(
            real_estate=re_obj, component_type="roof", name="Dach", installation_year=2020
        )
        asset_obj = Asset.objects.create(user=self.admin_user, name="Konto", value=Decimal("1000.00"))
        AssetSnapshot.objects.create(
            user=self.admin_user,
            content_type=ContentType.objects.get_for_model(Asset),
            object_id=asset_obj.pk,
            date=datetime.date(2026, 1, 1),
            value=Decimal("1000.00"),
        )

        self.client.force_login(self.admin_user)
        r_ins = self.client.get(reverse("admin:finance_insurancepolicy_changelist"), HTTP_ACCEPT_LANGUAGE="de")
        self.assertEqual(r_ins.status_code, 200)
        self.assertContains(r_ins, "Versicherungspolicen")

        r_comp = self.client.get(reverse("admin:finance_propertycomponent_changelist"), HTTP_ACCEPT_LANGUAGE="de")
        self.assertEqual(r_comp.status_code, 200)
        self.assertContains(r_comp, "Bauteilbezeichnung / Spezifikation")

        r_snap = self.client.get(reverse("admin:finance_assetsnapshot_changelist"), HTTP_ACCEPT_LANGUAGE="de")
        self.assertEqual(r_snap.status_code, 200)
        self.assertContains(r_snap, "Vermögenswert / Objekt")
        self.assertContains(r_snap, "Monatliche Nettorente (€)")
        self.assertContains(r_snap, "Wert")

    def test_admin_filters_out_expired_and_future_cashflows_but_keeps_existing_link(self):
        today = timezone.localdate()
        expired_cf = CashFlowSource.objects.create(
            user=self.admin_user,
            name="Abgelaufene Police",
            value=Decimal("20.00"),
            is_income=False,
            start_date=today - datetime.timedelta(days=400),
            end_date=today - datetime.timedelta(days=10),
        )
        future_cf = CashFlowSource.objects.create(
            user=self.admin_user,
            name="Zukünftige Police",
            value=Decimal("30.00"),
            is_income=False,
            start_date=today + datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=375),
        )
        self.client.force_login(self.admin_user)

        add_html = self.client.get(reverse("admin:finance_insurancepolicy_add")).content.decode("utf-8")
        self.assertNotIn(f'value="{expired_cf.pk}"', add_html)
        self.assertNotIn(f'value="{future_cf.pk}"', add_html)
        self.assertIn(f'<option value="{self.admin_cf_free.pk}">', add_html)

        legacy_policy = InsurancePolicy.objects.create(
            user=self.admin_user,
            name="Altvertrag",
            premium_amount=Decimal("20.00"),
            linked_cash_flow=expired_cf,
        )
        change_html = self.client.get(
            reverse("admin:finance_insurancepolicy_change", args=[legacy_policy.pk])
        ).content.decode("utf-8")
        self.assertIn(f'<option value="{expired_cf.pk}" selected>', change_html)

    def test_annual_adjustment_wizard_relinks_insurance_and_updates_premium(self):
        from finance.models import ImportFilter

        today = timezone.localdate()
        old_cf = CashFlowSource.objects.create(
            user=self.admin_user,
            name="KFZ Schutz",
            value=Decimal("50.00"),
            is_income=False,
            frequency="monthly",
            start_date=today - datetime.timedelta(days=365),
        )
        policy = InsurancePolicy.objects.create(
            user=self.admin_user,
            name="KFZ Police",
            insurance_type="kfz",
            premium_amount=Decimal("50.00"),
            payment_frequency="monthly",
            linked_cash_flow=old_cf,
        )
        imp_filter = ImportFilter.objects.create(
            user=self.admin_user,
            target_name="KFZ Abbuchung",
            linked_cash_flow=old_cf,
        )

        self.client.force_login(self.admin_user)
        resp = self.client.post(
            reverse("finance:cash_flow_annual_adjustment"),
            {
                "selected_items": [str(old_cf.pk)],
                "new_start_date": today.isoformat(),
                "adjustment_percent": "10",
            },
        )
        self.assertEqual(resp.status_code, 302)

        old_cf.refresh_from_db()
        self.assertEqual(old_cf.end_date, today - datetime.timedelta(days=1))

        new_cf = CashFlowSource.objects.filter(user=self.admin_user, name="KFZ Schutz").exclude(pk=old_cf.pk).get()
        self.assertEqual(new_cf.value, Decimal("55.00"))

        policy.refresh_from_db()
        self.assertEqual(policy.linked_cash_flow_id, new_cf.pk)
        self.assertEqual(policy.premium_amount, Decimal("55.00"))

        imp_filter.refresh_from_db()
        self.assertEqual(imp_filter.linked_cash_flow_id, new_cf.pk)

        add_html = self.client.get(reverse("admin:finance_insurancepolicy_add")).content.decode("utf-8")
        self.assertNotIn(f'value="{old_cf.pk}"', add_html)
        self.assertIn(f'<option value="{new_cf.pk}" disabled="disabled">', add_html)

        new_cf.value = Decimal("60.00")
        new_cf.save()
        policy.refresh_from_db()
        self.assertEqual(policy.premium_amount, Decimal("60.00"))

    def test_admin_changelists_default_to_current_user_when_multiple_users_exist(self):
        from finance.models import PropertyComponent, RealEstate

        other_policy = InsurancePolicy.objects.create(
            user=self.other_user, name="Other Policy Only", premium_amount=Decimal("12.00")
        )
        admin_re = RealEstate.objects.create(user=self.admin_user, name="Admin Haus", property_value=Decimal("200000"))
        other_re = RealEstate.objects.create(user=self.other_user, name="Other Haus", property_value=Decimal("150000"))
        admin_comp = PropertyComponent.objects.create(
            real_estate=admin_re, component_type="roof", name="Admin Dach", installation_year=2020
        )
        other_comp = PropertyComponent.objects.create(
            real_estate=other_re, component_type="roof", name="Other Dach", installation_year=2019
        )

        self.client.force_login(self.admin_user)

        # Default view filters to current user and marks "(Du)" selected
        ins_resp = self.client.get(reverse("admin:finance_insurancepolicy_changelist"))
        self.assertEqual(ins_resp.status_code, 200)
        self.assertContains(ins_resp, self.existing_policy.name)
        self.assertNotContains(ins_resp, other_policy.name)
        self.assertContains(ins_resp, f"?user={self.admin_user.pk}")
        self.assertContains(ins_resp, "Alle Benutzer anzeigen")

        # Switching to ?user=all reveals other user's policy
        ins_all = self.client.get(reverse("admin:finance_insurancepolicy_changelist") + "?user=all")
        self.assertContains(ins_all, self.existing_policy.name)
        self.assertContains(ins_all, other_policy.name)

        # Related-user admin (PropertyComponentAdmin) defaults to current user
        comp_resp = self.client.get(reverse("admin:finance_propertycomponent_changelist"))
        self.assertContains(comp_resp, admin_comp.name)
        self.assertNotContains(comp_resp, other_comp.name)
        comp_all = self.client.get(reverse("admin:finance_propertycomponent_changelist") + "?user=all")
        self.assertContains(comp_all, other_comp.name)

        # PK-based user views (FinancialStatusProxyAdmin & CustomUserAdmin) default to current user
        fs_resp = self.client.get(reverse("admin:finance_financialstatusproxy_changelist"))
        self.assertEqual([u.pk for u in fs_resp.context["cl"].result_list], [self.admin_user.pk])
        fs_all = self.client.get(reverse("admin:finance_financialstatusproxy_changelist") + "?user=all")
        self.assertEqual({u.pk for u in fs_all.context["cl"].result_list}, {self.admin_user.pk, self.other_user.pk})

        cu_resp = self.client.get(reverse("admin:core_customuser_changelist"))
        self.assertEqual([u.pk for u in cu_resp.context["cl"].result_list], [self.admin_user.pk])
        cu_all = self.client.get(reverse("admin:core_customuser_changelist") + "?user=all")
        self.assertEqual({u.pk for u in cu_all.context["cl"].result_list}, {self.admin_user.pk, self.other_user.pk})

        # Standard staff user sees only own objects and no user switcher filter
        from django.contrib.auth.models import Permission
        view_perm = Permission.objects.get(codename="view_insurancepolicy")
        self.other_user.user_permissions.add(view_perm)
        self.other_user.is_staff = True
        self.other_user.save(update_fields=["is_staff"])
        self.client.force_login(self.other_user)
        staff_resp = self.client.get(reverse("admin:finance_insurancepolicy_changelist"))
        self.assertEqual(staff_resp.status_code, 200)
        self.assertContains(staff_resp, other_policy.name)
        self.assertNotContains(staff_resp, self.existing_policy.name)
        self.assertNotContains(staff_resp, "Alle Benutzer anzeigen")

        # When only 1 active user remains, superuser sees no user filter sidebar
        self.other_user.is_active = False
        self.other_user.save(update_fields=["is_active"])
        self.client.force_login(self.admin_user)
        single_resp = self.client.get(reverse("admin:finance_insurancepolicy_changelist"))
        self.assertEqual(single_resp.status_code, 200)
        self.assertNotContains(single_resp, "Alle Benutzer anzeigen")

        # CategoryAdmin column renders "Systemkategorie" in German
        cat_resp = self.client.get(reverse("admin:finance_category_changelist"), HTTP_ACCEPT_LANGUAGE="de")
        self.assertEqual(cat_resp.status_code, 200)
        self.assertContains(cat_resp, "Systemkategorie")


class AssetModalSaveTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="asset_u", password="AssetPassword123!")
        self.asset = Asset.objects.create(
            user=self.user,
            name="Tagesgeld Alt",
            asset_type="overnight",
            institution="",
            value=Decimal("5000.00"),
            growth_rate=Decimal("2.50"),
            monthly_savings_amount=Decimal("100.00"),
            is_emergency_fund=False,
            withdrawal_amount=Decimal("50.00"),
        )

    def test_asset_modal_save_updates_institution_and_emergency_fund(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("finance:asset_edit", args=[self.asset.pk]),
            {
                "current_tab": "all",
                "name": "Tagesgeld Neu",
                "asset_type": "overnight",
                "institution": "ING DiBa",
                "isin_ticker": "",
                "value": "5500.00",
                "growth_rate": "",
                "monthly_savings_amount": "",
                "is_emergency_fund": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, "Tagesgeld Neu")
        self.assertEqual(self.asset.institution, "ING DiBa")
        self.assertTrue(self.asset.is_emergency_fund)
        self.assertEqual(self.asset.withdrawal_amount, Decimal("50.00"))

        resp_off = self.client.post(
            reverse("finance:asset_edit", args=[self.asset.pk]),
            {
                "current_tab": "all",
                "name": "Tagesgeld Neu",
                "asset_type": "overnight",
                "institution": "DKB",
                "isin_ticker": "",
                "value": "5500.00",
                "growth_rate": "3.00",
                "monthly_savings_amount": "0.00",
            },
        )
        self.assertEqual(resp_off.status_code, 302)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.institution, "DKB")
        self.assertFalse(self.asset.is_emergency_fund)

    def test_benutzer_group_permissions_and_admin_tenant_isolation(self):
        from finance.models import RealEstate
        new_user = CustomUser.objects.create_user(username="std_user", password="StdPassword123!")
        other_user = CustomUser.objects.create_user(username="other_std", password="OtherPassword123!")
        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(new_user.groups.filter(name="Benutzer").exists())

        for perm_code in (
            "finance.add_insurancepolicy",
            "finance.change_insurancepolicy",
            "finance.view_insurancepolicy",
            "finance.add_propertycomponent",
            "finance.add_document",
            "finance.add_loanextrarepayment",
            "finance.add_importfilter",
            "finance.view_financialstatusproxy",
            "core.view_customuser",
            "core.change_customuser",
        ):
            self.assertTrue(new_user.has_perm(perm_code), f"Missing permission: {perm_code}")

        own_re = RealEstate.objects.create(user=new_user, name="Eigenes Haus", property_value=Decimal("400000"))
        foreign_re = RealEstate.objects.create(user=other_user, name="Fremdes Geheimhaus", property_value=Decimal("900000"))

        self.client.force_login(new_user)
        comp_add_resp = self.client.get(reverse("admin:finance_propertycomponent_add"))
        self.assertEqual(comp_add_resp.status_code, 200)
        self.assertContains(comp_add_resp, own_re.name)
        self.assertNotContains(comp_add_resp, foreign_re.name)

        loan_add_resp = self.client.get(reverse("admin:finance_loan_add"))
        self.assertEqual(loan_add_resp.status_code, 200)
        self.assertContains(loan_add_resp, own_re.name)
        self.assertNotContains(loan_add_resp, foreign_re.name)

    def test_land_property_type_tax_reserves_and_risk_audit(self):
        from finance.forms import RealEstateForm
        from finance.models import RealEstate
        from finance.services_realestate import (
            calculate_property_tax_metrics,
            calculate_reserve_metrics_for_property,
        )
        from finance.services_risk import calculate_protection_audit

        land_user = CustomUser.objects.create_user(username="land_owner", password="LandPassword123!")

        form = RealEstateForm(
            data={
                "name": "Ackerland Nord",
                "property_type": "land",
                "property_value": "120000.00",
                "appreciation_rate": "1.50",
                "rental_income_monthly": "250.00",
                "maintenance_costs_monthly": "20.00",
                "ancillary_costs_monthly": "10.00",
                "living_space_sqm": "15000.00",
                "is_rental_property": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        land = form.save(commit=False)
        land.user = land_user
        land.save()

        self.assertEqual(land.building_share_percent, Decimal("0.00"))
        self.assertEqual(land.depreciation_rate_percent, Decimal("0.00"))

        res_metrics = calculate_reserve_metrics_for_property(land)
        self.assertTrue(res_metrics["is_land"])
        self.assertIsNone(res_metrics["building_age"])
        self.assertEqual(res_metrics["peters_monthly"], Decimal("0.00"))
        self.assertEqual(res_metrics["iibv_monthly"], Decimal("0.00"))
        self.assertTrue(res_metrics["is_sufficient"])

        tax_metrics = calculate_property_tax_metrics(land, [])
        self.assertEqual(tax_metrics["building_value"], Decimal("0.00"))
        self.assertEqual(tax_metrics["annual_afa"], Decimal("0.00"))
        self.assertEqual(tax_metrics["annual_rental_income"], Decimal("3000.00"))

        # Non-land property with explicit 0% building share must not fall back to 70%
        zero_share_house = RealEstate.objects.create(
            user=land_user,
            name="Sonderobjekt 0% AfA",
            property_type="commercial",
            property_value=Decimal("100000.00"),
            building_share_percent=Decimal("0.00"),
            depreciation_rate_percent=Decimal("0.00"),
        )
        zero_tax = calculate_property_tax_metrics(zero_share_house, [])
        self.assertEqual(zero_tax["building_value"], Decimal("0.00"))
        self.assertEqual(zero_tax["annual_afa"], Decimal("0.00"))

        # Land only -> no mandatory building insurance in audit
        zero_share_house.delete()
        audit_land_only = calculate_protection_audit(land_user)
        self.assertNotIn("building", [c["type"] for c in audit_land_only["checklist"]])

        # Adding a house -> building insurance required
        RealEstate.objects.create(
            user=land_user,
            name="Wohnhaus",
            property_type="house",
            property_value=Decimal("350000.00"),
        )
        audit_with_house = calculate_protection_audit(land_user)
        self.assertIn("building", [c["type"] for c in audit_with_house["checklist"]])

    def test_unified_documents_vault_secure_download_and_global_search(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from finance.models import Document, RealEstate

        owner = CustomUser.objects.create_user(username="doc_owner", password="DocPassword123!")
        intruder = CustomUser.objects.create_user(username="doc_intruder", password="IntPassword123!")

        re_obj = RealEstate.objects.create(user=owner, name="Mietwohnung Mitte", property_value=Decimal("250000.00"))
        ins_obj = InsurancePolicy.objects.create(user=owner, name="Allianz Haftpflicht", premium_amount=Decimal("8.50"))
        foreign_ins = InsurancePolicy.objects.create(user=intruder, name="Geheime Fremdpolice", premium_amount=Decimal("99.00"))

        self.client.force_login(owner)
        upload_resp = self.client.post(
            reverse("finance:document_upload"),
            {
                "domain": "insurance",
                "insurance_policy": ins_obj.id,
                "title": "Haftpflicht Police 2026",
                "category": "insurance",
                "date": "2026-01-15",
                "amount": "102.00",
                "notes": "Policennummer XYZ-9988",
                "file": SimpleUploadedFile("police.txt", b"Police Inhalt", content_type="text/plain"),
                "next": "/finance/pensions/?tab=documents",
            },
        )
        self.assertEqual(upload_resp.status_code, 302)
        doc = Document.objects.get(user=owner, title="Haftpflicht Police 2026")
        self.assertEqual(doc.domain, "insurance")
        self.assertEqual(doc.insurance_policy_id, ins_obj.id)

        # Also create a PDF-text-indexed doc & real estate invoice
        Document.objects.create(
            user=owner,
            domain="real_estate",
            real_estate=re_obj,
            title="Heizungsrechnung 2026",
            category="maintenance_invoice",
            file=SimpleUploadedFile("heizung.txt", b"Rechnung", content_type="text/plain"),
            amount=Decimal("450.00"),
            extracted_text="Rechnungsnummer RE-2026-777 Brennerwartung",
        )

        # Vault & contextual views render HTTP 200
        self.assertEqual(self.client.get(reverse("finance:documents_vault")).status_code, 200)
        self.assertEqual(self.client.get(reverse("finance:pension_plan")).status_code, 200)
        self.assertEqual(self.client.get(reverse("finance:assets_overview")).status_code, 200)
        self.assertEqual(self.client.get(reverse("finance:real_estate_loans")).status_code, 200)

        # Global search finds PDF extracted_text & insurance policy, never foreign data
        search_resp = self.client.get(reverse("finance:global_search"), {"q": "RE-2026-777"})
        self.assertEqual(search_resp.status_code, 200)
        self.assertContains(search_resp, "Heizungsrechnung 2026")
        self.assertNotContains(search_resp, foreign_ins.name)

        search_all_resp = self.client.get(reverse("finance:global_search"))
        self.assertEqual(search_all_resp.status_code, 200)
        self.assertContains(search_all_resp, "Allianz Haftpflicht")
        self.assertNotContains(search_all_resp, foreign_ins.name)

        # Owner can download; intruder gets 404 on download and delete
        dl_owner = self.client.get(reverse("finance:document_download", args=[doc.id]))
        self.assertEqual(dl_owner.status_code, 200)
        dl_owner.close()

        self.client.force_login(intruder)
        self.assertEqual(self.client.get(reverse("finance:document_download", args=[doc.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("finance:document_delete", args=[doc.id])).status_code, 404)
        self.assertTrue(Document.objects.filter(pk=doc.id).exists())

        # Cleanup uploaded files
        for d in Document.objects.filter(user=owner):
            if d.file:
                d.file.delete(save=False)
