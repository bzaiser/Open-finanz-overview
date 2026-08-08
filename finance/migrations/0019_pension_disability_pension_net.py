# Generated manually for disability_pension_net additions

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0018_assetsnapshot_expected_payout_net'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='disability_pension_net',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Full disability monthly net payout from statutory pension statement', max_digits=10, null=True, verbose_name='Disability Pension Net (€/month)'),
        ),
        migrations.AddField(
            model_name='assetsnapshot',
            name='disability_pension_net',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Disability Pension Net (€)'),
        ),
    ]
