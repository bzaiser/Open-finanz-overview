# Generated for Pension model retirement_age and target_pension_payout fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0016_pension_gross_payout_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='retirement_age',
            field=models.PositiveIntegerField(blank=True, help_text='Target retirement age for this specific pension contract (e.g. 67)', null=True, verbose_name='Retirement Age'),
        ),
        migrations.AddField(
            model_name='pension',
            name='target_pension_payout',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Target net monthly payout desired for this specific contract', max_digits=12, null=True, verbose_name='Target Monthly Payout (€)'),
        ),
    ]
