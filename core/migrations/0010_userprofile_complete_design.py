from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_userprofile_pension_increase'),
    ]

    operations = [
        # UserProfile - Field additions
        migrations.AddField(
            model_name='userprofile',
            name='primary_color',
            field=models.CharField(default='#0d6efd', max_length=7, verbose_name='Primary Color'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='secondary_color',
            field=models.CharField(default='#6c757d', max_length=7, verbose_name='Secondary Color'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='background_color',
            field=models.CharField(default='#ffffff', max_length=7, verbose_name='Background Color'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='text_color',
            field=models.CharField(default='#212529', max_length=7, verbose_name='Text Color'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='sidebar_bg_color',
            field=models.CharField(default='#f8f9fa', max_length=7, verbose_name='Sidebar Background'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='table_header_bg_color',
            field=models.CharField(default='#212529', max_length=7, verbose_name='Table Header Background'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='table_header_text_color',
            field=models.CharField(default='#ffffff', max_length=7, verbose_name='Table Header Text'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='table_border_color',
            field=models.CharField(default='#dee2e6', max_length=7, verbose_name='Table Border Color'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='physical_asset_growth_rate',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name='Default Physical Asset Growth (%)'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='real_estate_growth_rate',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name='Default Real Estate Growth (%)'),
        ),

        # Theme - Field additions
        migrations.AddField(
            model_name='theme',
            name='primary_color',
            field=models.CharField(default='#0d6efd', max_length=7, verbose_name='Primary Color'),
        ),
        migrations.AddField(
            model_name='theme',
            name='secondary_color',
            field=models.CharField(default='#6c757d', max_length=7, verbose_name='Secondary Color'),
        ),
        migrations.AddField(
            model_name='theme',
            name='background_color',
            field=models.CharField(default='#ffffff', max_length=7, verbose_name='Background Color'),
        ),
        migrations.AddField(
            model_name='theme',
            name='text_color',
            field=models.CharField(default='#212529', max_length=7, verbose_name='Text Color'),
        ),
        migrations.AddField(
            model_name='theme',
            name='sidebar_bg_color',
            field=models.CharField(default='#f8f9fa', max_length=7, verbose_name='Sidebar Background'),
        ),
        migrations.AddField(
            model_name='theme',
            name='table_header_bg_color',
            field=models.CharField(default='#212529', max_length=7, verbose_name='Table Header Background'),
        ),
        migrations.AddField(
            model_name='theme',
            name='table_header_text_color',
            field=models.CharField(default='#ffffff', max_length=7, verbose_name='Table Header Text'),
        ),
        migrations.AddField(
            model_name='theme',
            name='table_border_color',
            field=models.CharField(default='#dee2e6', max_length=7, verbose_name='Table Border Color'),
        ),

        # Altering existing fields to match final model state (removing help_text if needed)
        migrations.AlterField(
            model_name='userprofile',
            name='gradient_end',
            field=models.CharField(default='#0d6efd', max_length=7, verbose_name='Gradient End Color'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='gradient_start',
            field=models.CharField(default='#6610f2', max_length=7, verbose_name='Gradient Start Color'),
        ),
    ]
