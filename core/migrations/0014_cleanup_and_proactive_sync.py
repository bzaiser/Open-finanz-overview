from django.db import migrations

def cleanup_and_sync_all(apps, schema_editor):
    """
    Cleans up redundant admin themes and synchronizes all existing user themes
    and final profile styles.
    """
    try:
        CoreTheme = apps.get_model('core', 'Theme')
        UserProfile = apps.get_model('core', 'UserProfile')
        AdminTheme = apps.get_model('admin_interface', 'Theme')
    except (LookupError, Exception):
        return

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

    # 1. DELETE junk themes
    # We keep only themes that exist in our CoreTheme table or were created for a user's style
    valid_names = list(CoreTheme.objects.values_list('name', flat=True))
    # Add potential user style names
    for up in UserProfile.objects.all():
        valid_names.append(f"User {up.user.username} Style")
    
    # Delete themes not in our valid list
    AdminTheme.objects.exclude(name__in=valid_names).delete()

    # 2. PROACTIVE SYNC for each core theme
    for theme in CoreTheme.objects.all():
        admin_theme, _ = AdminTheme.objects.get_or_create(name=theme.name)
        
        primary = theme.primary_color or "#0d6efd"
        secondary = theme.secondary_color or "#6c757d"
        is_dark = get_brightness(primary) < 128
        text_color = "#ffffff" if is_dark else "#212529"

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
        admin_theme.save()

    # 3. SYNC ACTIVE Profiles
    for up in UserProfile.objects.all():
        name = up.theme.name if up.theme else f"User {up.user.username} Style"
        admin_theme, _ = AdminTheme.objects.get_or_create(name=name)
        
        primary = up.primary_color or "#0d6efd"
        secondary = up.secondary_color or "#6c757d"
        is_dark = get_brightness(primary) < 128
        text_color = "#ffffff" if is_dark else "#212529"

        admin_theme.title = "Finanzplan Admin"
        admin_theme.css_header_background_color = primary
        admin_theme.css_header_text_color = text_color
        admin_theme.css_module_background_color = primary
        admin_theme.css_save_button_background_color = primary
        admin_theme.css_save_button_background_hover_color = secondary
        admin_theme.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_sync_admin_interface_themes'),
    ]

    operations = [
        migrations.RunPython(cleanup_and_sync_all, migrations.RunPython.noop),
    ]
