# Generated by Django 2.0 on 2019-04-01 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('week_scheduler', '0003_auto_20190401_1554'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userlogging',
            name='activity_id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
