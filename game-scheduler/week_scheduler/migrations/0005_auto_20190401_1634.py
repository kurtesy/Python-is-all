# Generated by Django 2.0 on 2019-04-01 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('week_scheduler', '0004_auto_20190401_1621'),
    ]

    operations = [
        migrations.AddField(
            model_name='historymodel',
            name='action',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='historymodel',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
