from django.utils.translation import gettext_lazy as _

STATES = [
    {"index": 1, "n": _("1. OK / Ampel Grün"), "h": 142, "t": _("✓ Stabil"), "side": 1},
    {"index": 2, "n": _("2. Positiv / Info"), "h": 185, "t": _("ℹ Info"), "side": 1},
    {"index": 3, "n": _("3. Mittel / Achtung"), "h": 43, "t": _("⚠ Achtung"), "side": 2},
    {"index": 4, "n": _("4. Warnung"), "h": 26, "t": _("⚡ Warnung"), "side": 2},
    {"index": 5, "n": _("5. Schlecht / Negativ"), "h": 4, "t": _("✕ Fehler"), "side": 2},
    {"index": 6, "n": _("6. Gefahr / Kritisch"), "h": 338, "t": _("🛑 Gefahr"), "side": 2},
    {"index": 7, "n": _("7. Neutral / Inaktiv"), "h": None, "t": _("• Inaktiv"), "side": 0},
    {"index": 8, "n": _("8. Fokus / Highlight"), "h": 272, "t": _("★ Fokus"), "side": 1},
]

MOODS = {
    "modern":    {"s": 70, "l": 50, "bg": "#f4f6f9", "dark": False, "shift": 0.06},
    "dualtone":  {"s": 78, "l": 52, "bg": "#f4f6f9", "dark": False, "shift": 0.00, "dual": True},
    "serioes":   {"s": 42, "l": 45, "bg": "#f1f5f9", "dark": False, "shift": 0.10},
    "dunkel":    {"s": 65, "l": 52, "bg": "#0f172a", "dark": True,  "shift": 0.08},
    "brutalism": {"s": 92, "l": 56, "bg": "#050505", "dark": True,  "shift": 0.00, "brutal": True},
    "wellness":  {"s": 36, "l": 74, "bg": "#f6f7f4", "dark": False, "shift": 0.18},
    "ecofuture": {"s": 88, "l": 52, "bg": "#141d18", "dark": True,  "shift": 0.05, "eco": True},
    "moody":     {"s": 58, "l": 36, "bg": "#16131c", "dark": True,  "shift": 0.12},
    "fancy":     {"s": 65, "l": 68, "bg": "#f8f5fc", "dark": False, "shift": 0.12},
    "vintage":   {"s": 48, "l": 54, "bg": "#f5f0e6", "dark": False, "shift": 0.25, "warm": True},
    "knallbunt": {"s": 95, "l": 52, "bg": "#f4f6f9", "dark": False, "shift": 0.02},
    "neon":      {"s": 100,"l": 55, "bg": "#090a0f", "dark": True,  "shift": 0.00, "glow": True},
    "duester":   {"s": 35, "l": 38, "bg": "#111317", "dark": True,  "shift": 0.15},
    "earth":     {"s": 32, "l": 48, "bg": "#ede6dc", "dark": False, "shift": 0.15, "earth": True},
    "monochrom": {"s": 55, "l": 50, "bg": "#f4f6f9", "dark": False, "shift": 0.88},
    "grayscale": {"s": 0,  "l": 50, "bg": "#efefef", "dark": False, "shift": 0.00},
}


def hex_to_hsl(hex_str):
    if not hex_str or not isinstance(hex_str, str):
        return {"h": 217, "s": 91, "l": 60}
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return {"h": 217, "s": 91, "l": 60}
    try:
        r = int(clean[0:2], 16) / 255.0
        g = int(clean[2:4], 16) / 255.0
        b = int(clean[4:6], 16) / 255.0
    except ValueError:
        return {"h": 217, "s": 91, "l": 60}

    mx = max(r, g, b)
    mn = min(r, g, b)
    l = (mx + mn) / 2.0
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = (g - b) / d + (6.0 if g < b else 0.0)
        elif mx == g:
            h = (b - r) / d + 2.0
        else:
            h = (r - g) / d + 4.0
        h *= 60.0
    return {"h": round(h) % 360, "s": round(s * 100), "l": round(l * 100)}


def hsl_to_hex(h, s, l):
    h = h % 360
    s = max(0, min(100, s))
    l = max(0, min(100, l))
    l_norm = l / 100.0
    a = (s * min(l_norm, 1.0 - l_norm)) / 100.0

    def f(n):
        k = (n + h / 30.0) % 12.0
        color = l_norm - a * max(min(k - 3.0, 9.0 - k, 1.0), -1.0)
        return f"{round(255 * color):02x}"

    return f"#{f(0)}{f(8)}{f(4)}".upper()


def get_contrast_text(hex_str):
    hsl = hex_to_hsl(hex_str)
    return "#1e293b" if hsl["l"] >= 66 else "#ffffff"


def _compute_single_state(st_h, st_side, idx, base1, base2, mood_key, m, is_dark):
    hue = base1["h"] if st_h is None else round(st_h + (base1["h"] - st_h) * m["shift"])
    s = (0 if m["s"] == 0 else 12) if st_h is None else m["s"]
    l = m["l"]

    if m.get("dual"):
        if st_side == 1:
            hue = base1["h"]
            l = 46 if idx == 0 else (56 if idx == 1 else 38)
        elif st_side == 2:
            hue = base2["h"]
            l = min(68, 38 + (max(0, idx - 2) * 7))
        else:
            hue = round((base1["h"] + base2["h"]) / 2)
            s = 14
            l = 50

    if m.get("warm") and st_h is not None:
        hue = round(hue * 0.85 + 35 * 0.15)
    if m.get("earth"):
        hue = 32 if st_h is None else round(hue * 0.35 + 28 * 0.65)
        l = min(68, 35 + ((idx % 8) * 4))
    if m.get("eco") and st_h is not None:
        if st_h in (142, 185):
            s = 48
            l = 44
        else:
            s = 98
            l = 56
    if mood_key in ("monochrom", "grayscale"):
        l = min(76, 24 + ((idx % 8) * 7))
    elif not m.get("dual") and st_h is not None and 35 <= st_h <= 55 and not is_dark and mood_key != "wellness":
        l = max(48, l)

    hex_val = hsl_to_hex(hue, s, l)
    alpha = 0.24 if is_dark else 0.15
    bg = f"hsla({hue % 360}, {s}%, {l}%, {alpha})"
    txt = hsl_to_hex(hue, s, min(86, l + 24)) if is_dark else hsl_to_hex(hue, s, max(22, l - 26))
    card_text = get_contrast_text(hex_val)
    return {
        "hue": hue % 360,
        "s": s,
        "l": l,
        "hex": hex_val,
        "bg": bg,
        "txt": txt,
        "card_text": card_text,
    }


def compute_theme_palette(c1="#6610f2", c2="#0d6efd", mood_key="modern", bg_mode="auto", bg_custom="#e2e8f0"):
    if mood_key not in MOODS:
        mood_key = "modern"
    m = MOODS[mood_key]

    page_bg = m["bg"]
    is_dark = bool(m["dark"])
    if bg_mode == "light":
        page_bg = "#f4f6f9"
        is_dark = False
    elif bg_mode == "dark":
        page_bg = "#0f172a"
        is_dark = True
    elif bg_mode == "custom" and bg_custom:
        page_bg = bg_custom
        is_dark = hex_to_hsl(page_bg)["l"] < 50

    base1 = hex_to_hsl(c1)
    base2 = hex_to_hsl(c2)

    computed_states = []
    states_by_index = {}
    for idx, st in enumerate(STATES):
        res = _compute_single_state(st["h"], st["side"], idx, base1, base2, mood_key, m, is_dark)
        entry = {
            "index": st["index"],
            "name": str(st["n"]),
            "tag": str(st["t"]),
            **res,
        }
        computed_states.append(entry)
        states_by_index[st["index"]] = entry

    primary_hex = "#555555" if mood_key == "grayscale" else c1
    grad_start = "#333333" if mood_key == "grayscale" else c1
    grad_end = "#888888" if mood_key == "grayscale" else c2

    text_color = "#f8fafc" if is_dark else "#1e293b"
    sidebar_bg = hsl_to_hex(base1["h"], min(25, m["s"]), 12 if is_dark else 96)
    table_header_bg = hsl_to_hex(base1["h"], m["s"], 28 if is_dark else max(32, min(52, m["l"])))
    table_header_text = get_contrast_text(table_header_bg)
    table_body_bg = hsl_to_hex(base1["h"], min(18, m["s"]), 11 if is_dark else 99) if bg_mode != "custom" else page_bg
    table_body_text = text_color
    table_border = "#334155" if is_dark else "#dee2e6"

    return {
        "c1": grad_start,
        "c2": grad_end,
        "mood": mood_key,
        "bg_mode": bg_mode,
        "bg_custom": bg_custom,
        "is_dark": is_dark,
        "brutal": bool(m.get("brutal", False)),
        "glow": bool(m.get("glow", False) or m.get("eco", False)),
        "primary_color": primary_hex,
        "background_color": page_bg,
        "text_color": text_color,
        "sidebar_bg_color": sidebar_bg,
        "table_header_bg_color": table_header_bg,
        "table_header_text_color": table_header_text,
        "table_body_bg_color": table_body_bg,
        "table_body_text_color": table_body_text,
        "table_border_color": table_border,
        "states": computed_states,
        "states_by_index": states_by_index,
    }


def get_profile_theme_studio_settings(profile):
    if not profile:
        return {
            "c1": "#6610f2",
            "c2": "#0d6efd",
            "mood": "modern",
            "bg_mode": "auto",
            "bg_custom": "#ffffff",
            "sync_cards_and_charts": True,
        }
    dc = profile.dashboard_config or {}
    ts = dc.get("theme_studio", {})
    return {
        "c1": profile.gradient_start or "#6610f2",
        "c2": profile.gradient_end or "#0d6efd",
        "mood": ts.get("mood", "modern"),
        "bg_mode": ts.get("bg_mode", "auto"),
        "bg_custom": ts.get("bg_custom", profile.background_color or "#ffffff"),
        "sync_cards_and_charts": ts.get("sync_cards_and_charts", True),
    }


def get_profile_theme_palette(profile):
    s = get_profile_theme_studio_settings(profile)
    return compute_theme_palette(
        c1=s["c1"],
        c2=s["c2"],
        mood_key=s["mood"],
        bg_mode=s["bg_mode"],
        bg_custom=s["bg_custom"],
    )


def harmonize_category_color(raw_hex, idx, profile=None, is_income=False, palette=None):
    """
    Transforms a category's color (or assigns a distinct hue if default grey)
    using the user's active Design Studio mood.
    Returns dict: {'hex': ..., 'bg': ..., 'txt': ...}
    """
    if palette is None:
        palette = get_profile_theme_palette(profile)

    mood_key = palette["mood"]
    m = MOODS.get(mood_key, MOODS["modern"])
    is_dark = palette["is_dark"]
    base1 = hex_to_hsl(palette["c1"])
    base2 = hex_to_hsl(palette["c2"])

    clean_hex = (raw_hex or "").strip().lower()
    if not clean_hex or clean_hex in ("#6c757d", "#808080", "#adb5bd"):
        # Assign well-spaced golden-angle hue
        raw_hue = (idx * 137 + (140 if is_income else 15)) % 360
    else:
        raw_hue = hex_to_hsl(clean_hex)["h"]

    side = 1 if is_income else 2
    res = _compute_single_state(raw_hue, side, idx % 6, base1, base2, mood_key, m, is_dark)
    return {
        "hex": res["hex"],
        "bg": res["bg"],
        "txt": res["txt"],
    }


def get_harmonized_category_maps(profile=None):
    """
    Returns (by_name, by_id) where:
      by_name[cat.name] = harmonized_hex
      by_id[cat.id] = {'hex': ..., 'bg': ..., 'txt': ...}
    """
    from finance.models import Category
    palette = get_profile_theme_palette(profile)
    sync_enabled = get_profile_theme_studio_settings(profile).get("sync_cards_and_charts", True)

    by_name = {}
    by_id = {}
    for idx, cat in enumerate(Category.objects.all().order_by("id")):
        if sync_enabled:
            h_col = harmonize_category_color(cat.color, idx, profile=profile, palette=palette)
        else:
            raw = cat.color or "#6c757d"
            hsl = hex_to_hsl(raw)
            is_dark = palette["is_dark"]
            h_col = {
                "hex": raw,
                "bg": f"hsla({hsl['h']}, {hsl['s']}%, {hsl['l']}%, {0.24 if is_dark else 0.15})",
                "txt": hsl_to_hex(hsl["h"], hsl["s"], min(86, hsl["l"] + 24) if is_dark else max(22, hsl["l"] - 26)),
            }
        by_name[cat.name] = h_col["hex"]
        by_name[cat.translated_name] = h_col["hex"]
        by_id[cat.id] = h_col

    return by_name, by_id
