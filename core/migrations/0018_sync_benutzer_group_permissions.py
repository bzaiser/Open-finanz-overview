from django.db import migrations
from django.contrib.auth.management import create_permissions


def sync_benutzer_group_permissions(apps, schema_editor):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    CustomUser = apps.get_model('core', 'CustomUser')

    group, _ = Group.objects.get_or_create(name='Benutzer')

    crud_models = [
        ('core', 'userprofile'),
        ('finance', 'asset'),
        ('finance', 'cashflowsource'),
        ('finance', 'realestate'),
        ('finance', 'propertycomponent'),
        ('finance', 'propertydocument'),
        ('finance', 'loan'),
        ('finance', 'loanextrarepayment'),
        ('finance', 'pension'),
        ('finance', 'insurancepolicy'),
        ('finance', 'onetimeevent'),
        ('finance', 'physicalasset'),
        ('finance', 'assetsnapshot'),
        ('finance', 'importbatch'),
        ('finance', 'pendingtransaction'),
        ('finance', 'processedtransactionhash'),
        ('finance', 'importfilter'),
        ('finance', 'categorizationmemory'),
        ('finance', 'category'),
    ]
    view_change_models = [
        ('core', 'customuser'),
        ('finance', 'financialstatusproxy'),
    ]
    view_models = [
        ('admin_interface', 'theme'),
        ('core', 'editablepagecontent'),
    ]

    perms = []
    for app_label, model_name in crud_models:
        perms.extend(list(Permission.objects.filter(
            content_type__app_label=app_label,
            content_type__model=model_name,
        )))
    for app_label, model_name in view_change_models:
        perms.extend(list(Permission.objects.filter(
            content_type__app_label=app_label,
            content_type__model=model_name,
            codename__in=[f'view_{model_name}', f'change_{model_name}'],
        )))
    for app_label, model_name in view_models:
        perms.extend(list(Permission.objects.filter(
            content_type__app_label=app_label,
            content_type__model=model_name,
            codename__startswith='view_',
        )))

    group.permissions.set(perms)

    for user in CustomUser.objects.filter(is_superuser=False):
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
        user.groups.add(group)


def reverse_sync(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_alter_userprofile_table_header_bg_color'),
        ('finance', '0033_cashflowsource_owner_role_loan_owner_role_and_more'),
    ]

    operations = [
        migrations.RunPython(sync_benutzer_group_permissions, reverse_code=reverse_sync),
    ]
