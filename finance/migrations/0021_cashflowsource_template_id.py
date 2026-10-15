from django.db import migrations, models

def migrate_existing_tpl_ids(apps, schema_editor):
    CashFlowSource = apps.get_model('finance', 'CashFlowSource')
    for cfs in CashFlowSource.objects.all():
        if cfs.notes and 'tpl_id:' in cfs.notes:
            cleaned_lines = []
            found_tpl_id = None
            for line in cfs.notes.splitlines():
                if line.startswith('tpl_id:'):
                    found_tpl_id = line.split(':', 1)[1].strip()
                else:
                    cleaned_lines.append(line)
            if found_tpl_id:
                cfs.template_id = found_tpl_id
                cfs.notes = '\n'.join(cleaned_lines).strip()
                cfs.save(update_fields=['template_id', 'notes'])

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0020_alter_pension_help_texts'),
    ]

    operations = [
        migrations.AddField(
            model_name='cashflowsource',
            name='template_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name='Template ID'
            ),
        ),
        migrations.RunPython(migrate_existing_tpl_ids, migrations.RunPython.noop),
    ]
