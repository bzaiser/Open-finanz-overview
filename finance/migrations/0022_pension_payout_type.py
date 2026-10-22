from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0021_cashflowsource_template_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='payout_type',
            field=models.CharField(
                choices=[
                    ('monthly', 'Monthly Pension (Laufende Rente)'),
                    ('one_time', 'Lump-Sum Payout (Einmalige Kapitalabfindung)'),
                ],
                default='monthly',
                help_text='Monthly pension or one-time capital settlement',
                max_length=20,
                verbose_name='Payout Type'
            ),
        ),
    ]
