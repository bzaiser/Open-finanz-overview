from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_pendingtransaction_ai_confidence_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='interest_teaser_rate',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Higher promotional interest rate (e.g. for new customers)', max_digits=5, null=True, verbose_name='Teaser Interest Rate (%)'),
        ),
        migrations.AddField(
            model_name='asset',
            name='interest_teaser_until',
            field=models.DateField(blank=True, help_text='Date when the teaser rate expires and falls back to the standard growth rate', null=True, verbose_name='Teaser Rate Expiry Date'),
        ),
    ]
