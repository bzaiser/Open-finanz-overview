from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_theme_gradient_end_theme_gradient_start'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='pension_increase',
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                max_digits=5,
                verbose_name='Default Pension Increase (%)',
            ),
        ),
    ]
