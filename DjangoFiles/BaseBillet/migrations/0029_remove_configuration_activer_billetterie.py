# Generated by Django 3.2 on 2022-09-14 05:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('BaseBillet', '0028_auto_20220826_1559'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='configuration',
            name='activer_billetterie',
        ),
    ]
