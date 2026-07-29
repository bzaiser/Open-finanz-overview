# Generated manually for Statutory Pension & Pension Points tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0012_physicalasset_acquisition_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='pension_type',
            field=models.CharField(choices=[('capital', 'Capital / Private Pension'), ('statutory', 'Statutory Pension (Gesetzliche Rente)')], default='capital', max_length=20, verbose_name='Pension Type'),
        ),
        migrations.AddField(
            model_name='pension',
            name='pension_points',
            field=models.DecimalField(blank=True, decimal_places=4, help_text='Number of statutory pension points accumulated', max_digits=8, null=True, verbose_name='Pension Points (Entgeltpunkte)'),
        ),
        migrations.AddField(
            model_name='pension',
            name='point_value',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Value of 1 pension point in EUR (e.g. 39.32)', max_digits=6, null=True, verbose_name='Point Value (€)'),
        ),
        migrations.AddField(
            model_name='assetsnapshot',
            name='pension_points',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True, verbose_name='Pension Points (Entgeltpunkte)'),
        ),
        migrations.AddField(
            model_name='assetsnapshot',
            name='point_value',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Point Value (€)'),
        ),
    ]
