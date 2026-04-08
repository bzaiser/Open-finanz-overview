# Generated manually to avoid Docker permission issues

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_importfilter_unique_filter_per_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingtransaction',
            name='raw_signatures',
            field=models.TextField(blank=True, help_text='Semicolon-separated MD5 hashes of original Excel rows', null=True, verbose_name='Raw Row Fingerprints'),
        ),
    ]
