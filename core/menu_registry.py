from django.urls import reverse
from django.utils.translation import gettext_lazy as _

try:
    from design_studio.menu import MENU_ICON_CHOICES
except ImportError:
    MENU_ICON_CHOICES = [
        ("bi-speedometer2", _("Dashboard / Tacho")),
        ("bi-arrow-down-up", _("Transaktionen / Pfeile")),
        ("bi-bank", _("Bank / Altersvorsorge")),
        ("bi-houses", _("Immobilien / Häuser")),
        ("bi-pie-chart", _("Portfolio / Torte")),
        ("bi-magic", _("Zauberstab / Import")),
        ("bi-search", _("Suche / Lupe")),
        ("bi-folder2-open", _("Dokumente / Ordner")),
        ("bi-gear", _("Einstellungen / Zahnrad")),
        ("bi-shield-lock", _("Admin / Schild")),
        ("bi-moon-stars", _("Tag / Nacht")),
    ]

DEFAULT_MENU_ITEMS = [
    {
        "id": "dashboard",
        "url_name": "finance:dashboard",
        "match_urls": ["dashboard"],
        "default_label": _("Dashboard"),
        "icon": "bi-speedometer2",
        "zone": "main",
        "display": "icon_text",
        "visible": True,
        "order": 1,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "cash_flow",
        "url_name": "finance:cash_flow_list",
        "match_urls": ["cash_flow_list"],
        "default_label": _("Transactions"),
        "icon": "bi-arrow-down-up",
        "zone": "main",
        "display": "icon_text",
        "visible": True,
        "order": 2,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "pension_plan",
        "url_name": "finance:pension_plan",
        "match_urls": ["pension_plan"],
        "default_label": _("Retirement Planning"),
        "icon": "bi-bank",
        "zone": "main",
        "display": "icon_text",
        "visible": True,
        "order": 3,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "real_estate",
        "url_name": "finance:real_estate_loans",
        "match_urls": ["real_estate_loans"],
        "default_label": _("Real Estate & Loans"),
        "icon": "bi-houses",
        "zone": "main",
        "display": "icon_text",
        "visible": True,
        "order": 4,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "assets",
        "url_name": "finance:assets_overview",
        "match_urls": ["assets_overview"],
        "default_label": _("Portfolio"),
        "icon": "bi-pie-chart",
        "zone": "main",
        "display": "icon_text",
        "visible": True,
        "order": 5,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "bank_import",
        "url_name": "finance:import_transactions",
        "match_urls": ["import_transactions"],
        "default_label": _("Bank Import"),
        "icon": "bi-magic",
        "zone": "main",
        "display": "icon_text",
        "visible": False,
        "order": 6,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "global_search",
        "url_name": "finance:global_search",
        "match_urls": ["global_search"],
        "default_label": _("Global Search"),
        "icon": "bi-search",
        "zone": "utility",
        "display": "icon_only",
        "visible": True,
        "order": 1,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "documents",
        "url_name": "finance:documents_vault",
        "match_urls": ["documents_vault"],
        "default_label": _("Documents"),
        "icon": "bi-folder2-open",
        "zone": "utility",
        "display": "icon_only",
        "visible": True,
        "order": 2,
        "locked": False,
        "staff_only": False,
    },
    {
        "id": "settings",
        "url_name": "profile",
        "match_urls": ["profile"],
        "default_label": _("Settings"),
        "icon": "bi-gear",
        "zone": "utility",
        "display": "icon_only",
        "visible": True,
        "order": 3,
        "locked": True,
        "staff_only": False,
    },
    {
        "id": "ops_updates",
        "url_name": "ops_kit:updates",
        "match_urls": ["updates"],
        "default_label": _("Auto-Updates"),
        "icon": "bi-cloud-download",
        "zone": "utility",
        "display": "icon_only",
        "visible": True,
        "order": 4,
        "locked": False,
        "staff_only": True,
    },
    {
        "id": "admin",
        "url_name": "admin:index",
        "match_urls": [],
        "default_label": _("Administration"),
        "icon": "bi-shield-lock",
        "zone": "utility",
        "display": "icon_only",
        "visible": True,
        "order": 4,
        "locked": False,
        "staff_only": True,
    },
    {
        "id": "night_mode",
        "url_name": "toggle_night_mode",
        "match_urls": [],
        "default_label": _("Tag / Nacht"),
        "icon": "bi-moon-stars",
        "zone": "utility",
        "display": "icon_only",
        "visible": True,
        "order": 5,
        "locked": False,
        "staff_only": False,
    },
]


def resolve_user_menu(user):
    """
    Resolves the user's customized menu configuration (visibility, display mode,
    zone, custom label, custom icon, and order) merged with DEFAULT_MENU_ITEMS.
    """
    profile = getattr(user, "profile", None) if (user and getattr(user, "is_authenticated", False)) else None
    dc = (profile.dashboard_config or {}) if profile else {}
    saved_list = dc.get("menu_config") if isinstance(dc.get("menu_config"), list) else []
    saved_map = {
        entry.get("id"): entry
        for entry in saved_list
        if isinstance(entry, dict) and entry.get("id")
    }
    is_staff = bool(getattr(user, "is_staff", False))

    resolved = []
    for idx, item in enumerate(DEFAULT_MENU_ITEMS):
        if item["staff_only"] and not is_staff:
            continue
        ov = saved_map.get(item["id"], {})
        custom_label = (ov.get("label") or "").strip()
        icon = (ov.get("icon") or "").strip()
        if not icon.startswith("bi-"):
            icon = item["icon"]
        zone = ov.get("zone") if ov.get("zone") in ("main", "utility") else item["zone"]
        display = ov.get("display") if ov.get("display") in ("icon_text", "icon_only", "text_only") else item["display"]
        visible = True if item["locked"] else bool(ov.get("visible", item["visible"]))
        try:
            order = int(ov.get("order", idx + 1))
        except (TypeError, ValueError):
            order = idx + 1

        try:
            url = reverse(item["url_name"])
        except Exception:
            url = "#"

        resolved.append({
            "id": item["id"],
            "url": url,
            "match_urls": item["match_urls"],
            "default_label": str(item["default_label"]),
            "custom_label": custom_label,
            "label": custom_label or str(item["default_label"]),
            "icon": icon,
            "zone": zone,
            "display": display,
            "visible": visible,
            "order": order,
            "locked": item["locked"],
        })

    resolved.sort(key=lambda x: (0 if x["zone"] == "main" else 1, x["order"]))
    main_items = [x for x in resolved if x["visible"] and x["zone"] == "main"]
    utility_items = [x for x in resolved if x["visible"] and x["zone"] == "utility"]

    return {
        "all_items": resolved,
        "main_items": main_items,
        "utility_items": utility_items,
        "icon_choices": [(ic, str(lbl)) for ic, lbl in MENU_ICON_CHOICES],
    }
