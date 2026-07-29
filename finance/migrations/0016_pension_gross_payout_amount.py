# Generated manually for gross payout amount field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0015_pension_social_deduction_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='gross_payout_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Calculated automatically from points * point_value, or enter manually', max_digits=10, null=True, verbose_name='Gross Monthly Payout (€)'),
        ),
    ]
