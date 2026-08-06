# Generated for UserProfile target_pension_payout field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_userprofile_retirement_age'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='target_pension_payout',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Target net monthly payout at retirement for pension gap analysis.', max_digits=12, null=True, verbose_name='Target Monthly Pension Payout (€)'),
        ),
    ]
