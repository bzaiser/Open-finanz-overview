from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_userprofile_partner_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='hide_wizard_on_start',
            field=models.BooleanField(default=False, verbose_name='Hide Setup Wizard on Startup'),
        ),
    ]
