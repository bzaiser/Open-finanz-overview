from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0017_pension_retirement_age_target_payout'),
    ]

    operations = [
        migrations.AddField(
            model_name='assetsnapshot',
            name='expected_payout_net',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Monthly Net Payout (€)'),
        ),
    ]
