# Generated manually for UserProfile retirement_age field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_remove_userprofile_physical_asset_growth_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='retirement_age',
            field=models.PositiveIntegerField(default=67, help_text='Target retirement age for planning and gap calculation (default 67)', verbose_name='Retirement Age'),
        ),
    ]
