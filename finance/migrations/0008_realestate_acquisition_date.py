from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0007_alter_financialstatusproxy_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='realestate',
            name='acquisition_date',
            field=models.DateField(blank=True, null=True, verbose_name='Acquisition Date'),
        ),
    ]
