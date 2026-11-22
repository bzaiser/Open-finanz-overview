from design_studio.engine import (
    BG_SVG_MODES,
    CARD_SURFACES,
    DEFAULT_SETTINGS,
    FONT_FAMILIES,
    FONT_SCALES,
    MENU_LAYOUTS,
    MENU_STYLES,
    MOODS,
    STATES,
    _compute_single_state,
    compute_theme_palette,
    get_contrast_text,
    hex_to_hsl,
    hsl_to_hex,
    normalize_settings,
)


def get_profile_theme_studio_settings(profile):
    if not profile:
        return normalize_settings({})
    dc = profile.dashboard_config or {}
    ts = dict(dc.get("theme_studio") or {})
    if "c1" not in ts and getattr(profile, "gradient_start", None):
        ts["c1"] = profile.gradient_start
    if "c2" not in ts and getattr(profile, "gradient_end", None):
        ts["c2"] = profile.gradient_end
    if "bg_custom" not in ts and getattr(profile, "background_color", None):
        ts["bg_custom"] = profile.background_color
    return normalize_settings(ts)


def get_profile_theme_palette(profile):
    s = get_profile_theme_studio_settings(profile)
    return compute_theme_palette(
        c1=s["c1"],
        c2=s["c2"],
        mood_key=s["mood"],
        bg_mode=s["bg_mode"],
        bg_custom=s["bg_custom"],
        state_overrides=s.get("state_overrides"),
        table_header_color=s.get("table_header_color", ""),
    )


def apply_theme_studio_to_profile(profile, theme_studio_data, manual_precision=False):
    """
    Applies Design Studio settings (mood, bg_mode, bg_custom, sync_cards_and_charts, etc.)
    to `profile` (colors, dashboard_config, cards, and auto_night_mode flag).
    Returns the computed theme palette dict.
    """
    from finance.card_registry import apply_theme_palette_to_cards

    dc = dict(profile.dashboard_config or {})
    prev_ts = dc.get("theme_studio") if isinstance(dc.get("theme_studio"), dict) else {}
    preserved_keys = (
        "brand_title", "brand_icon", "menu_config", "default_genre",
        "genre_photos_enabled", "table_header_color", "ui_zoom",
        "glass_alpha", "glass_blur", "bg_strength", "menu_layout",
        "menu_style", "font_family", "font_scale",
    )
    raw_ts = {k: prev_ts[k] for k in preserved_keys if k in prev_ts}
    raw_ts.update(dict(theme_studio_data or {}))
    if "c1" not in raw_ts and getattr(profile, "gradient_start", None):
        raw_ts["c1"] = profile.gradient_start
    if "c2" not in raw_ts and getattr(profile, "gradient_end", None):
        raw_ts["c2"] = profile.gradient_end
    norm = normalize_settings(raw_ts)

    dc["theme_studio"] = norm

    palette = compute_theme_palette(
        c1=norm["c1"],
        c2=norm["c2"],
        mood_key=norm["mood"],
        bg_mode=norm["bg_mode"],
        bg_custom=norm["bg_custom"],
        state_overrides=norm.get("state_overrides"),
        table_header_color=norm.get("table_header_color", ""),
    )

    profile.auto_night_mode = bool(palette["is_dark"])
    sync_cards = bool(norm.get("sync_cards_and_charts", True))
    if sync_cards and not manual_precision:
        profile.primary_color = palette["primary_color"]
        profile.background_color = palette["background_color"]
        profile.text_color = palette["text_color"]
        profile.sidebar_bg_color = palette["sidebar_bg_color"]
        profile.table_header_bg_color = palette["table_header_bg_color"]
        profile.table_header_text_color = palette["table_header_text_color"]
        profile.table_filter_bg_color = palette.get("table_filter_bg_color") or (
            "rgba(255,255,255,0.06)" if palette["is_dark"] else "rgba(0,0,0,0.05)"
        )
        profile.table_body_bg_color = palette["table_body_bg_color"]
        profile.table_body_text_color = palette["table_body_text_color"]
        profile.table_border_color = palette["table_border_color"]

    if sync_cards:
        dc = apply_theme_palette_to_cards(dc, palette)

    profile.dashboard_config = dc
    return palette


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


class FinanzplanDesignStudioAdapter:
    """Bridges design_studio saves directly into UserProfile.dashboard_config."""

    def get_settings(self, user):
        profile = getattr(user, "profile", None) if (user and getattr(user, "is_authenticated", False)) else None
        return get_profile_theme_studio_settings(profile)

    def save_settings(self, user, settings_dict, palette=None, manual_precision=False):
        profile = getattr(user, "profile", None) if (user and getattr(user, "is_authenticated", False)) else None
        if not profile:
            return palette
        out_palette = apply_theme_studio_to_profile(profile, settings_dict, manual_precision=manual_precision)
        dc = dict(profile.dashboard_config or {})
        if "menu_config" in settings_dict:
            dc["menu_config"] = settings_dict["menu_config"]
        profile.dashboard_config = dc
        profile.save()
        return out_palette
