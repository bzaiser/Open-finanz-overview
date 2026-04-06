from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_remove_theme_and_related_field'),
    ]

    operations = [
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
            name='table_filter_bg_color',
            field=models.CharField(default='#f1f3f5', max_length=7, verbose_name='Table Filter Background'),
        ),
    ]
