from .card_registry import get_user_card_groups, CARD_REGISTRY, MODULE_GROUPS

def card_config_context(request):
    """
    Supplies card configuration data, registry definitions, and dashboard layout
    to all templates when the user is authenticated.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    from .views import SUMMARY_WIDGETS, AVAILABLE_CHARTS, DEFAULT_LAYOUT, DEFAULT_SUMMARY_LAYOUT

    profile = getattr(user, 'profile', None)
    dashboard_config = (profile.dashboard_config or {}) if profile else {}

    # 1. Summary layout for dashboard
    raw_summary_layout = dashboard_config.get('summary_layout', DEFAULT_SUMMARY_LAYOUT)
    resolved_summary_layout = []
    existing_ids = set()
    for item in raw_summary_layout:
        if isinstance(item, dict) and 'id' in item:
            resolved_summary_layout.append(dict(item))
            existing_ids.add(item['id'])

    for widget_id, widget_info in SUMMARY_WIDGETS.items():
        if widget_id not in existing_ids:
            resolved_summary_layout.append({
                'id': widget_id,
                'visible': True,
                'bg_color': widget_info.get('default_bg', '#6c757d'),
                'text_color': widget_info.get('default_text', '#ffffff'),
                'order': len(resolved_summary_layout) + 1
            })

    # 2. Charts layout for dashboard
    raw_layout = dashboard_config.get('layout', DEFAULT_LAYOUT)
    resolved_layout = []
    existing_chart_ids = set()
    for item in raw_layout:
        if isinstance(item, dict) and 'id' in item:
            resolved_layout.append(dict(item))
            existing_chart_ids.add(item['id'])

    for chart_id, chart_info in AVAILABLE_CHARTS.items():
        if chart_id not in existing_chart_ids:
            resolved_layout.append({
                'id': chart_id,
                'visible': False,
                'width': chart_info.get('default_width', 6),
                'height': chart_info.get('default_height', 'medium'),
                'order': len(resolved_layout) + 1
            })

    # 3. Card groups for all modules
    user_card_groups = get_user_card_groups(user)

    # 4. Backup Due Evaluation & Auto-Backup
    backup_due = False
    backup_auto_success = False
    if profile:
        from core.backup_service import is_backup_due, save_backup_to_directory
        if is_backup_due(profile):
            if profile.backup_path:
                # Automatic silent background backup to configured path
                success, path, msg = save_backup_to_directory(profile.backup_path, max_keep=profile.backup_max_keep)
                if success:
                    from django.utils import timezone
                    profile.backup_last_run = timezone.now()
                    profile.save(update_fields=['backup_last_run'])
                    backup_auto_success = True
                else:
                    backup_due = True
            else:
                backup_due = True

    return {
        'card_config_user_groups': user_card_groups,
        'card_config_registry': CARD_REGISTRY,
        'card_config_module_groups': MODULE_GROUPS,
        'card_config_summary_widgets': SUMMARY_WIDGETS,
        'card_config_available_charts': AVAILABLE_CHARTS,
        'card_config_summary_layout': resolved_summary_layout,
        'card_config_layout': resolved_layout,
        'backup_due': backup_due,
        'backup_auto_success': backup_auto_success,
    }
