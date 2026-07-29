# Generated manually for Pension notes field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_pension_statutory_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='pension',
            name='notes',
            field=models.TextField(blank=True, help_text='Additional multiline notes or details', null=True, verbose_name='Notes'),
        ),
    ]
