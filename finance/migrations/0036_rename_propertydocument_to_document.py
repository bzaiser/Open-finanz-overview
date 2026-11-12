# Generated manually from 0036 to preserve existing PropertyDocument rows

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_document_users(apps, schema_editor):
    Document = apps.get_model('finance', 'Document')
    for doc in Document.objects.select_related('real_estate').all():
        if doc.user_id is None and doc.real_estate_id is not None:
            doc.user_id = doc.real_estate.user_id
            doc.domain = 'real_estate'
            doc.save(update_fields=['user', 'domain'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0035_realestate_property_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PropertyDocument',
            new_name='Document',
        ),
        migrations.AlterModelOptions(
            name='document',
            options={'ordering': ['-date', '-uploaded_at'], 'verbose_name': 'Document', 'verbose_name_plural': 'Documents'},
        ),
        migrations.AddField(
            model_name='document',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='document',
            name='domain',
            field=models.CharField(
                choices=[
                    ('real_estate', 'Real Estate'),
                    ('loan', 'Loans & Financing'),
                    ('insurance', 'Insurance Policies'),
                    ('pension', 'Pensions & Retirement'),
                    ('asset', 'Bank Accounts & Securities'),
                    ('physical_asset', 'Physical Assets'),
                    ('general', 'Taxes & General'),
                ],
                default='real_estate',
                max_length=25,
                verbose_name='Domain',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='loan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='finance.loan', verbose_name='Loan'),
        ),
        migrations.AddField(
            model_name='document',
            name='insurance_policy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='finance.insurancepolicy', verbose_name='Insurance Policy'),
        ),
        migrations.AddField(
            model_name='document',
            name='pension',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='finance.pension', verbose_name='Pension'),
        ),
        migrations.AddField(
            model_name='document',
            name='asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='finance.asset', verbose_name='Account / Asset'),
        ),
        migrations.AddField(
            model_name='document',
            name='physical_asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='finance.physicalasset', verbose_name='Physical Asset'),
        ),
        migrations.AddField(
            model_name='document',
            name='extracted_text',
            field=models.TextField(blank=True, verbose_name='Extracted Text'),
        ),
        migrations.AlterField(
            model_name='document',
            name='real_estate',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='finance.realestate', verbose_name='Real Estate'),
        ),
        migrations.AlterField(
            model_name='document',
            name='category',
            field=models.CharField(
                choices=[
                    ('contract', 'Purchase / Notary Contract'),
                    ('land_register', 'Land Register Excerpt'),
                    ('energy_cert', 'Energy Performance Certificate'),
                    ('lease', 'Tenancy / Lease Agreement'),
                    ('maintenance_invoice', 'Renovation / Craftsman Invoice'),
                    ('loan_agreement', 'Loan / Financing Agreement'),
                    ('interest_cert', 'Interest Certificate / Annual Statement'),
                    ('repayment_plan', 'Repayment Plan / Extra Repayment Receipt'),
                    ('insurance', 'Insurance Policy / Certificate'),
                    ('premium_invoice', 'Premium Invoice / Contribution Notice'),
                    ('policy_amendment', 'Policy Amendment / Addendum'),
                    ('claim_correspondence', 'Claim / Correspondence'),
                    ('pension_info', 'Annual Pension Information'),
                    ('pension_notice', 'Pension Decision / Contract'),
                    ('bank_statement', 'Account Opening / Bank Statement'),
                    ('depot_statement', 'Securities / Depot Statement'),
                    ('tax_cert', 'Annual Tax Certificate'),
                    ('exemption_order', 'Tax Exemption Order'),
                    ('valuation', 'Appraisal / Valuation'),
                    ('tax_statement', 'Property Tax / Tax Assessment'),
                    ('other', 'Other Document'),
                ],
                default='other',
                max_length=30,
                verbose_name='Category',
            ),
        ),
        migrations.AlterField(
            model_name='document',
            name='file',
            field=models.FileField(upload_to='documents/%Y/%m/', verbose_name='File'),
        ),
        migrations.AlterField(
            model_name='document',
            name='amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Optional: Invoice or contract amount', max_digits=12, null=True, verbose_name='Amount (€)'),
        ),
        migrations.RunPython(backfill_document_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='document',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
    ]
