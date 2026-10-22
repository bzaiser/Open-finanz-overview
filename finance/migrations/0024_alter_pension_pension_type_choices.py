from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0023_alter_pension_payout_type_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pension',
            name='pension_type',
            field=models.CharField(
                choices=[
                    ('capital', 'Kapital- / Private Rentenversicherung'),
                    ('statutory', 'Gesetzliche Rente (DRV)'),
                    ('civil_service', 'Beamtenpension / Ruhegehalt'),
                    ('occupational_fund', 'Berufsständisches Versorgungswerk / VBL'),
                ],
                default='capital',
                max_length=20,
                verbose_name='Pension Type',
            ),
        ),
    ]
