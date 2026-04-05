from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_userprofile_physical_asset_growth_rate_and_more'),
    ]

    operations = [
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
            name='table_filter_bg_color',
            field=models.CharField(default='#f1f3f5', max_length=7, verbose_name='Table Filter Background'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='table_body_bg_color',
            field=models.CharField(default='#ffffff', max_length=7, verbose_name='Table Body Background'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='table_body_text_color',
            field=models.CharField(default='#212529', max_length=7, verbose_name='Table Body Text'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='table_border_color',
            field=models.CharField(default='#dee2e6', max_length=7, verbose_name='Table Border Color'),
        ),
    ]
