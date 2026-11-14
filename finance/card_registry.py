from django.utils.translation import gettext_lazy as _

CARD_REGISTRY = {
    # 1. Cash Flow
    'cash_flow': {
        'title': _("Einnahmen & Ausgaben"),
        'module': 'cashflow',
        'cards': [
            {
                'id': 'monthly_income',
                'title': _("Monatliche Einnahmen"),
                'icon': 'bi-graph-up-arrow',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'monthly_expenses',
                'title': _("Monatliche Ausgaben"),
                'icon': 'bi-graph-down-arrow',
                'bg_color': '#dc3545',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'monthly_surplus',
                'title': _("Monatlicher Überschuss"),
                'icon': 'bi-piggy-bank',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
        ]
    },

    # 2. Altersvorsorge & Versicherungen (4 Gruppen)
    'pension_top': {
        'title': _("Altersvorsorge: Übersicht (Kopfbereich)"),
        'module': 'pension',
        'section': 'top',
        'cards': [
            {
                'id': 'pension_top_total',
                'title': _("Vorsorge & Rentenbasis"),
                'icon': 'bi-piggy-bank',
                'bg_color': '#6f42c1',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'pension_top_check',
                'title': _("Absicherungs-Check"),
                'icon': 'bi-shield-check',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'pension_top_insurances',
                'title': _("Versicherungsbeiträge"),
                'icon': 'bi-file-earmark-check',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'pension_top_risk',
                'title': _("Notfall- & Risikopuffer"),
                'icon': 'bi-shield-shaded',
                'bg_color': '#0dcaf0',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'pension_tab_pensions': {
        'title': _("Tab: Altersvorsorge"),
        'module': 'pension',
        'section': 'tab_pensions',
        'cards': [
            {
                'id': 'pension_tab_statutory',
                'title': _("Gesetzliche Rente"),
                'icon': 'bi-cash-stack',
                'bg_color': '#fd7e14',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'pension_tab_private',
                'title': _("Private Altersvorsorge"),
                'icon': 'bi-wallet2',
                'bg_color': '#0dcaf0',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'pension_tab_total',
                'title': _("Gesamte Netto-Rente"),
                'icon': 'bi-graph-up-arrow',
                'bg_color': '#6f42c1',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'pension_tab_gap',
                'title': _("Rentenlücke / Überschuss"),
                'icon': 'bi-exclamation-triangle',
                'bg_color': '#dc3545',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'pension_tab_insurances': {
        'title': _("Tab: Versicherungen"),
        'module': 'pension',
        'section': 'tab_insurances',
        'cards': [
            {
                'id': 'ins_tab_monthly',
                'title': _("Monatliche Beiträge"),
                'icon': 'bi-wallet2',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'ins_tab_bu',
                'title': _("BU-Schutz gesamt (Mt.)"),
                'icon': 'bi-heart-pulse',
                'bg_color': '#fd7e14',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'ins_tab_life',
                'title': _("Risikolebens-Schutz"),
                'icon': 'bi-people',
                'bg_color': '#0dcaf0',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'ins_tab_quote',
                'title': _("Basis-Schutz Quote"),
                'icon': 'bi-shield-check',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'pension_tab_risk': {
        'title': _("Tab: Risiko-Check"),
        'module': 'pension',
        'section': 'tab_risk',
        'cards': [
            {
                'id': 'risk_tab_emergency',
                'title': _("Notgroschen & Puffer"),
                'icon': 'bi-piggy-bank',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'risk_tab_jobloss',
                'title': _("Jobverlust-Puffer (ALG I)"),
                'icon': 'bi-briefcase',
                'bg_color': '#0dcaf0',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'risk_tab_disability',
                'title': _("Berufsunfähigkeit (BU)"),
                'icon': 'bi-heart-pulse',
                'bg_color': '#dc3545',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'risk_tab_survivor',
                'title': _("Hinterbliebenenschutz"),
                'icon': 'bi-shield-shaded',
                'bg_color': '#6f42c1',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },

    # 3. Immobilien & Kredite (4 Gruppen)
    'real_estate_top': {
        'title': _("Immobilien: Übersicht (Kopfbereich)"),
        'module': 'real_estate',
        'section': 'top',
        'cards': [
            {
                'id': 're_top_property_value',
                'title': _("Gesamtwert Immobilien"),
                'icon': 'bi-houses',
                'bg_color': '#20c997',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 're_top_debt',
                'title': _("Restschuld Darlehen"),
                'icon': 'bi-bank',
                'bg_color': '#746d6d',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 're_top_equity',
                'title': _("Nettowert / Eigenkapital"),
                'icon': 'bi-pie-chart',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 're_top_cashflow',
                'title': _("Netto-Cashflow (Mieten)"),
                'icon': 'bi-cash-coin',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'real_estate_tab_renovation': {
        'title': _("Tab: Modernisierung & Sanierung"),
        'module': 'real_estate',
        'section': 'tab_renovation',
        'cards': [
            {
                'id': 'renov_tab_open',
                'title': _("Rücklagenbestand"),
                'icon': 'bi-piggy-bank',
                'bg_color': '#20c997',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'renov_tab_costs',
                'title': _("Ziel-Rücklage (Peters)"),
                'icon': 'bi-calculator',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'renov_tab_invested',
                'title': _("Bedarf nächste 5 Jahre"),
                'icon': 'bi-tools',
                'bg_color': '#746d6d',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'renov_tab_completed',
                'title': _("5-Jahres-Deckung"),
                'icon': 'bi-shield-check',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'real_estate_tab_calendar': {
        'title': _("Tab: Fristen & Kalender"),
        'module': 'real_estate',
        'section': 'tab_calendar',
        'cards': [
            {
                'id': 'cal_tab_rent',
                'title': _("Gesamte Jahresmiete"),
                'icon': 'bi-wallet2',
                'bg_color': '#20c997',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'cal_tab_debt',
                'title': _("Gesamter Schuldendienst"),
                'icon': 'bi-bank',
                'bg_color': '#746d6d',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'cal_tab_operating',
                'title': _("Betriebs- & Rücklagenkosten"),
                'icon': 'bi-tools',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'cal_tab_net',
                'title': _("Jährlicher Netto-Cashflow"),
                'icon': 'bi-graph-up-arrow',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'real_estate_tab_taxdocs': {
        'title': _("Tab: Steuer & Belege"),
        'module': 'real_estate',
        'section': 'tab_taxdocs',
        'cards': [
            {
                'id': 'tax_tab_rent',
                'title': _("Brutto-Mieteinnahmen (V+V)"),
                'icon': 'bi-wallet2',
                'bg_color': '#20c997',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'tax_tab_deductions',
                'title': _("Werbungskosten gesamt"),
                'icon': 'bi-file-earmark-minus',
                'bg_color': '#746d6d',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'tax_tab_result',
                'title': _("Steuerliches Ergebnis (V+V)"),
                'icon': 'bi-graph-up-arrow',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'tax_tab_impact',
                'title': _("Geschätzte Steuerwirkung"),
                'icon': 'bi-shield-shaded',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },

    # 4. Vermögen & Konten
    'assets_top': {
        'title': _("Vermögen & Konten"),
        'module': 'assets',
        'section': 'top',
        'cards': [
            {
                'id': 'assets_top_total',
                'title': _("Gesamtvermögen"),
                'icon': 'bi-cash-stack',
                'bg_color': '#ffc107',
                'text_color': '#212529',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'assets_top_cash',
                'title': _("Bankguthaben / Liquidität"),
                'icon': 'bi-wallet2',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'assets_top_depot',
                'title': _("Depots & Wertpapiere"),
                'icon': 'bi-graph-up',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'assets_top_physical',
                'title': _("Physische Sachwerte"),
                'icon': 'bi-gem',
                'bg_color': '#8a2be2',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
    'assets_tab_performance': {
        'title': _("Tab: Verlauf & Performance"),
        'module': 'assets',
        'section': 'tab_performance',
        'cards': [
            {
                'id': 'assets_perf_total',
                'title': _("Gesamtwert aktuell"),
                'icon': 'bi-wallet-fill',
                'bg_color': '#0d6efd',
                'text_color': '#ffffff',
                'order': 1,
                'visible': True,
            },
            {
                'id': 'assets_perf_change',
                'title': _("Wertentwicklung"),
                'icon': 'bi-graph-up-arrow',
                'bg_color': '#198754',
                'text_color': '#ffffff',
                'order': 2,
                'visible': True,
            },
            {
                'id': 'assets_perf_best',
                'title': _("Best-Performer"),
                'icon': 'bi-trophy-fill',
                'bg_color': '#6610f2',
                'text_color': '#ffffff',
                'order': 3,
                'visible': True,
            },
            {
                'id': 'assets_perf_largest',
                'title': _("Größte Position"),
                'icon': 'bi-pie-chart-fill',
                'bg_color': '#fd7e14',
                'text_color': '#ffffff',
                'order': 4,
                'visible': True,
            },
        ]
    },
}

MODULE_GROUPS = {
    'cashflow': ['cash_flow'],
    'pension': ['pension_top', 'pension_tab_pensions', 'pension_tab_insurances', 'pension_tab_risk'],
    'real_estate': ['real_estate_top', 'real_estate_tab_renovation', 'real_estate_tab_calendar', 'real_estate_tab_taxdocs'],
    'assets': ['assets_top', 'assets_tab_performance'],
}


def get_user_card_groups(user):
    """
    Returns a dict mapping group_key -> list of card dicts with user overrides applied.
    Each card dict has: id, title, icon, bg_color, text_color, visible, order.
    """
    profile = getattr(user, 'profile', None)
    dashboard_config = (profile.dashboard_config or {}) if profile else {}
    saved_groups = dashboard_config.get('card_groups', {})

    palette_states = {}
    if profile:
        from core.theme_engine import get_profile_theme_studio_settings, get_profile_theme_palette
        if get_profile_theme_studio_settings(profile).get('sync_cards_and_charts', True):
            palette_states = get_profile_theme_palette(profile).get('states_by_index', {})

    result = {}
    for group_key, group_def in CARD_REGISTRY.items():
        default_cards = {c['id']: dict(c) for c in group_def['cards']}
        user_group_cards = saved_groups.get(group_key, [])

        merged_cards = []
        seen_ids = set()

        # Apply saved user order & overrides
        for u_card in user_group_cards:
            cid = u_card.get('id')
            if cid in default_cards:
                c = dict(default_cards[cid])
                c['bg_color'] = u_card.get('bg_color') or c['bg_color']
                c['text_color'] = u_card.get('text_color') or c['text_color']
                c['visible'] = bool(u_card.get('visible', True))
                c['order'] = u_card.get('order', len(merged_cards) + 1)
                merged_cards.append(c)
                seen_ids.add(cid)

        # Append any new/missing default cards
        for cid, def_card in default_cards.items():
            if cid not in seen_ids:
                c = dict(def_card)
                if palette_states:
                    st_idx = CARD_SEMANTIC_STATE_MAP.get(cid, 2)
                    st = palette_states.get(st_idx)
                    if st:
                        c['bg_color'] = st['hex']
                        c['text_color'] = st['card_text']
                merged_cards.append(c)

        # Sort by order
        merged_cards.sort(key=lambda x: x.get('order', 999))
        result[group_key] = merged_cards

    return result


def get_user_card_group(user, group_key):
    """
    Returns the resolved, sorted list of cards for a specific group.
    """
    groups = get_user_card_groups(user)
    return groups.get(group_key, [])


# Mapping of all configurable KPI card IDs to the 8 semantic states of the Design Studio
# 1: OK/Green, 2: Positive/Info, 3: Medium/Amber, 4: Warning/Orange,
# 5: Negative/Red, 6: Critical/Rose, 7: Neutral/Gray, 8: Focus/Highlight
CARD_SEMANTIC_STATE_MAP = {
    # Dashboard summary_layout & Cashflow
    'monthly_income': 1,
    'monthly_expenses': 5,
    'monthly_surplus': 2,
    'current_assets': 2,
    'total_pensions': 2,
    'expected_payout': 8,
    'current_pension_payout': 3,
    'total_physical_assets': 8,
    'total_real_estate': 1,
    'total_combined_assets': 3,
    'total_debts': 6,

    # Pension module
    'pension_top_total': 8,
    'pension_top_check': 1,
    'pension_top_insurances': 2,
    'pension_top_risk': 3,
    'pension_tab_statutory': 4,
    'pension_tab_private': 2,
    'pension_tab_total': 8,
    'pension_tab_gap': 5,
    'ins_tab_monthly': 2,
    'ins_tab_bu': 4,
    'ins_tab_life': 2,
    'ins_tab_quote': 1,
    'risk_tab_emergency': 1,
    'risk_tab_jobloss': 2,
    'risk_tab_disability': 5,
    'risk_tab_survivor': 8,

    # Real Estate module
    're_top_property_value': 1,
    're_top_debt': 6,
    're_top_equity': 2,
    're_top_cashflow': 1,
    'renov_tab_open': 1,
    'renov_tab_costs': 2,
    'renov_tab_invested': 4,
    'renov_tab_completed': 1,
    'cal_tab_rent': 1,
    'cal_tab_debt': 5,
    'cal_tab_operating': 4,
    'cal_tab_net': 2,
    'tax_tab_rent': 1,
    'tax_tab_deductions': 4,
    'tax_tab_result': 2,
    'tax_tab_impact': 8,

    # Assets module
    'assets_top_total': 3,
    'assets_top_cash': 2,
    'assets_top_depot': 1,
    'assets_top_physical': 8,
    'assets_perf_total': 2,
    'assets_perf_change': 1,
    'assets_perf_best': 8,
    'assets_perf_largest': 4,
}


def apply_theme_palette_to_cards(dashboard_config, palette):
    """
    Harmonizes all configurable KPI cards in dashboard_config ('summary_layout' and 'card_groups')
    using the 8 semantic states of the given theme palette, while preserving visibility & order.
    """
    if not isinstance(dashboard_config, dict):
        dashboard_config = {}

    states_by_idx = palette.get('states_by_index', {})
    if not states_by_idx:
        return dashboard_config

    from .views import SUMMARY_WIDGETS, DEFAULT_SUMMARY_LAYOUT

    # 1. Harmonize Dashboard summary_layout
    raw_summary = dashboard_config.get('summary_layout') or list(DEFAULT_SUMMARY_LAYOUT)
    new_summary = []
    seen_summary_ids = set()
    for item in raw_summary:
        if isinstance(item, dict) and 'id' in item:
            wid = item['id']
            st_idx = CARD_SEMANTIC_STATE_MAP.get(wid, 2)
            st = states_by_idx.get(st_idx, states_by_idx.get(2, {}))
            updated = dict(item)
            if st:
                updated['bg_color'] = st['hex']
                updated['text_color'] = st['card_text']
            new_summary.append(updated)
            seen_summary_ids.add(wid)

    for wid, winfo in SUMMARY_WIDGETS.items():
        if wid not in seen_summary_ids:
            st_idx = CARD_SEMANTIC_STATE_MAP.get(wid, 2)
            st = states_by_idx.get(st_idx, states_by_idx.get(2, {}))
            new_summary.append({
                'id': wid,
                'visible': True,
                'bg_color': st.get('hex', winfo.get('default_bg', '#0d6efd')),
                'text_color': st.get('card_text', winfo.get('default_text', '#ffffff')),
                'order': len(new_summary) + 1,
            })
    dashboard_config['summary_layout'] = new_summary

    # 2. Harmonize all module card_groups in CARD_REGISTRY
    saved_groups = dashboard_config.get('card_groups') or {}
    new_groups = {}
    for group_key, group_def in CARD_REGISTRY.items():
        default_cards = {c['id']: dict(c) for c in group_def['cards']}
        user_cards = saved_groups.get(group_key, [])
        merged = []
        seen_cids = set()

        for uc in user_cards:
            cid = uc.get('id')
            if cid in default_cards:
                def_c = default_cards[cid]
                st_idx = CARD_SEMANTIC_STATE_MAP.get(cid, 2)
                st = states_by_idx.get(st_idx, states_by_idx.get(2, {}))
                merged.append({
                    'id': cid,
                    'visible': bool(uc.get('visible', True)),
                    'order': int(uc.get('order', len(merged) + 1)),
                    'bg_color': st.get('hex', def_c['bg_color']),
                    'text_color': st.get('card_text', def_c['text_color']),
                })
                seen_cids.add(cid)

        for cid, def_card in default_cards.items():
            if cid not in seen_cids:
                st_idx = CARD_SEMANTIC_STATE_MAP.get(cid, 2)
                st = states_by_idx.get(st_idx, states_by_idx.get(2, {}))
                merged.append({
                    'id': cid,
                    'visible': bool(def_card.get('visible', True)),
                    'order': int(def_card.get('order', len(merged) + 1)),
                    'bg_color': st.get('hex', def_card['bg_color']),
                    'text_color': st.get('card_text', def_card['text_color']),
                })

        merged.sort(key=lambda x: x.get('order', 999))
        new_groups[group_key] = merged

    dashboard_config['card_groups'] = new_groups
    return dashboard_config

