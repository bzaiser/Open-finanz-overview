from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0019_pension_disability_pension_net'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pension',
            name='disability_pension_net',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Pension in case of full reduction in earning capacity ('Wären Sie heute voll erwerbsgemindert...')",
                max_digits=10,
                null=True,
                verbose_name='Disability Pension Net (€/month)'
            ),
        ),
        migrations.AlterField(
            model_name='pension',
            name='expected_payout_at_retirement',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Projected regular old-age pension ('Sollten bis zum Rentenbeginn Beiträge gezahlt werden...')",
                max_digits=10,
                null=True,
                verbose_name='Expected Monthly Net Payout'
            ),
        ),
        migrations.AlterField(
            model_name='pension',
            name='social_deduction_rate',
            field=models.DecimalField(
                decimal_places=2,
                default=11.5,
                help_text='Deduction percentage for health & nursing care insurance (~11.5%)',
                max_digits=5,
                verbose_name='Social Security Deduction (%)'
            ),
        ),
    ]
