from django.db import migrations, models

def migrate_existing_payout_types(apps, schema_editor):
    Pension = apps.get_model('finance', 'Pension')
    for p in Pension.objects.all():
        if p.payout_type == 'monthly':
            if p.current_value and p.current_value > 0:
                p.payout_type = 'capital_drawdown'
            else:
                p.payout_type = 'lifelong_annuity'
            p.save(update_fields=['payout_type'])

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0022_pension_payout_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pension',
            name='payout_type',
            field=models.CharField(
                choices=[
                    ('capital_drawdown', 'Monatlicher Auszahlungsplan (Kapitalverzehr)'),
                    ('lifelong_annuity', 'Laufende Rente (Lebenslang)'),
                    ('one_time', 'Einmalige Kapitalabfindung (z. B. bAV)'),
                ],
                default='capital_drawdown',
                help_text='Auszahlungsart: Kapitalverzehr, lebenslange Rente oder Einmalabfindung',
                max_length=20,
                verbose_name='Payout Type'
            ),
        ),
        migrations.RunPython(migrate_existing_payout_types, migrations.RunPython.noop),
    ]
