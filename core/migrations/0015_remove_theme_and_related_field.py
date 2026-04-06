from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_cleanup_and_proactive_sync'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='theme',
        ),
        migrations.DeleteModel(
            name='Theme',
        ),
    ]
