from .models import UserProfile
from .theme_engine import (
    apply_theme_studio_to_profile,
    get_profile_theme_studio_settings,
)


class FinanzplanThemeAdapter:
    """
    Storage adapter bridging django-design-studio with Finanzplan's existing UserProfile
    without breaking changes or migrating existing user theme settings.
    Configure via: DESIGN_STUDIO_PROFILE_ADAPTER = "core.theme_adapter.FinanzplanThemeAdapter"
    """

    def get_settings(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return get_profile_theme_studio_settings(profile)

    def save_settings(self, user, settings_dict, palette=None, manual_precision=False):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if settings_dict.get("c1"):
            profile.gradient_start = settings_dict["c1"]
        if settings_dict.get("c2"):
            profile.gradient_end = settings_dict["c2"]
        res_palette = apply_theme_studio_to_profile(
            profile,
            settings_dict,
            manual_precision=manual_precision,
        )
        profile.save()
        return res_palette
