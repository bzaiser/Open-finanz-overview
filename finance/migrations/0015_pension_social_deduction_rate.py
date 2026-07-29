# Generated manually for statutory pension net payout deduction

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0014_pension_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='social_deduction_rate',
            field=models.DecimalField(decimal_places=2, default=11.5, help_text='Health and nursing care insurance deduction percentage (default ~11.5%)', max_digits=5, verbose_name='Social Security Deduction (%)'),
        ),
        migrations.AlterField(
            model_name='pension',
            name='expected_payout_at_retirement',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Net payout after KV/PV deductions (Enter manually or auto-calculated)', max_digits=10, null=True, verbose_name='Expected Monthly Net Payout'),
        ),
    ]
