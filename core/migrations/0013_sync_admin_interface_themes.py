from django.db import migrations

def sync_themes_to_admin(apps, schema_editor):
    """
    Proactively synchronizes all existing core.Theme objects to the django-admin-interface.
    This ensures that the user's 8 'Harmonien' are immediately available.
    """
    try:
        CoreTheme = apps.get_model('core', 'Theme')
        AdminTheme = apps.get_model('admin_interface', 'Theme')
    except (LookupError, Exception):
        # If admin_interface is not installed yet or app not found, skip
        return

    def get_brightness(hex_color):
        if not hex_color or len(hex_color) < 7:
            return 255
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (r * 299 + g * 587 + b * 114) / 1000

    for theme in CoreTheme.objects.all():
        # Get or create an admin theme with the same name
        admin_theme, created = AdminTheme.objects.get_or_create(name=theme.name)
        
        primary = theme.primary_color or "#0d6efd"
        secondary = theme.secondary_color or "#6c757d"
        is_dark = get_brightness(primary) < 128
        text_color = "#ffffff" if is_dark else "#212529"

        # Map fields to admin_interface.Theme
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
        
        # We don't activate them all; the user will select via profile
        # But we ensure they exist.
        admin_theme.save()

def reverse_sync(apps, schema_editor):
    # No action needed on reverse; we keep the admin themes
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_userprofile_complete_design'),
        ('admin_interface', '0001_initial'), # Ensure table exists
    ]

    operations = [
        migrations.RunPython(sync_themes_to_admin, reverse_sync),
    ]
