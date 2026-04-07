# Generated manually to repair broken migration chain and link to NAS history
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_physicalasset_sale_date_realestate_sale_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_system',
            field=models.BooleanField(default=False, verbose_name='System Category'),
        ),
    ]
