# Generated manually to bridge models with database
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0017_add_notes_and_consolidation_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingtransaction',
            name='planned_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Planned Amount'),
        ),
        migrations.AddField(
            model_name='importfilter',
            name='linked_cash_flow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_filters', to='finance.cashflowsource', verbose_name='Linked Cash Flow Source'),
        ),
    ]
