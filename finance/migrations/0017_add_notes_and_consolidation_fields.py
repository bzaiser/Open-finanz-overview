# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0016_importfilter'),
    ]

    operations = [
        migrations.AddField(
            model_name='cashflowsource',
            name='notes',
            field=models.TextField(blank=True, null=True, verbose_name='Notes'),
        ),
        migrations.AddField(
            model_name='pendingtransaction',
            name='integration_count',
            field=models.IntegerField(default=1, verbose_name='Integration Count'),
        ),
        migrations.AddField(
            model_name='pendingtransaction',
            name='matched_terms',
            field=models.TextField(blank=True, null=True, verbose_name='Matched Terms (Notes)'),
        ),
    ]
