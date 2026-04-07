# Generated manually to bridge models with database
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0018_plan_reconciliation'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingtransaction',
            name='signature',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True, verbose_name='Transaction Signature'),
        ),
        migrations.AddField(
            model_name='pendingtransaction',
            name='has_conflict',
            field=models.BooleanField(default=False, verbose_name='Has Plan Conflict'),
        ),
        migrations.AddField(
            model_name='pendingtransaction',
            name='is_confirmed',
            field=models.BooleanField(default=False, verbose_name='Confirmed Conflict'),
        ),
        migrations.AddField(
            model_name='pendingtransaction',
            name='existing_source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conflicting_transactions', to='finance.cashflowsource'),
        ),
    ]
