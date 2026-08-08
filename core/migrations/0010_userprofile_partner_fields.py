from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_userprofile_target_pension_payout'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='partner_name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Partner Name'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='partner_birth_date',
            field=models.DateField(blank=True, null=True, verbose_name='Partner Birth Date'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='partner_retirement_age',
            field=models.PositiveIntegerField(blank=True, default=67, null=True, verbose_name='Partner Retirement Age'),
        ),
    ]
