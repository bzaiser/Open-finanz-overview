# Generated manually to repair broken migration chain
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_alter_category_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_system',
            field=models.BooleanField(default=False, verbose_name='System Category'),
        ),
    ]
