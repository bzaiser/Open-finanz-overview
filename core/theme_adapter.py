from design_studio.engine import normalize_settings
from design_studio.storage import DefaultThemeStorageAdapter

from .models import UserProfile
from .theme_engine import apply_theme_studio_to_profile, get_profile_theme_studio_settings


class FinanzplanThemeAdapter(DefaultThemeStorageAdapter):
    """Bridges django-design-studio with Finanzplan's UserProfile without touching profile.html."""

    def get_settings(self, user):
        if user and getattr(user, "is_authenticated", False):
            profile, _ = UserProfile.objects.get_or_create(user=user)
            return normalize_settings(get_profile_theme_studio_settings(profile))
        return normalize_settings({})

    def save_settings(self, user, settings_dict, palette=None, manual_precision=False):
        norm = normalize_settings(settings_dict)
        if user and getattr(user, "is_authenticated", False):
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.gradient_start = norm["c1"]
            profile.gradient_end = norm["c2"]
            palette = apply_theme_studio_to_profile(profile, norm, manual_precision=manual_precision)
            profile.save()
        return palette
