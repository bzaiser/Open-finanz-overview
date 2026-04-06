from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.apps import apps
from .models import UserProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

def get_brightness(hex_color):
    """Calculates brightness, robust against invalid hex strings."""
    if not hex_color or not isinstance(hex_color, str) or not hex_color.startswith('#') or len(hex_color) < 7:
        return 255
    try:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000
    except (ValueError, IndexError):
        return 255

@receiver(post_save, sender=UserProfile)
def sync_admin_theme(sender, instance, **kwargs):
    """
    Synchronizes the user's current profile colors with the django-admin-interface theme.
    This follows the 'live' state of the profile fields, including manual overrides.
    """
    try:
        AdminTheme = apps.get_model('admin_interface', 'Theme')
        
        # Consistent name for the user's personal admin theme
        theme_name = f"Admin Theme ({instance.user.username})"
        
        admin_theme, created = AdminTheme.objects.get_or_create(name=theme_name)
        
        # Mapping colors DIRECTLY from UserProfile fields
        primary = instance.primary_color or "#0d6efd"
        secondary = instance.secondary_color or "#6c757d"
        is_dark = get_brightness(primary) < 128
        text_color = "#ffffff" if is_dark else "#212529"

        # Update Admin Theme fields
        admin_theme.title = "Finanzplan Admin"
        admin_theme.css_header_background_color = primary
        admin_theme.css_header_text_color = text_color
        admin_theme.css_header_link_color = text_color
        admin_theme.css_header_link_hover_color = secondary
        
        admin_theme.css_module_background_color = primary
        admin_theme.css_module_text_color = text_color
        admin_theme.css_module_link_color = secondary
        
        admin_theme.css_generic_link_color = primary
        admin_theme.css_save_button_background_color = primary
        admin_theme.css_save_button_text_color = text_color
        admin_theme.css_save_button_background_hover_color = secondary
        
        # Activate this theme and deactivate all others
        admin_theme.active = True
        admin_theme.save()
        
        AdminTheme.objects.exclude(pk=admin_theme.pk).update(active=False)
        print(f"DEBUG: Synchronized Admin Theme '{admin_theme.name}' (Colors: {primary}, {secondary})")
        
    except (LookupError, Exception) as e:
        print(f"DEBUG Error syncing admin theme: {e}")
