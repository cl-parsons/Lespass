# Generated by Django 2.2 on 2021-10-24 11:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('BaseBillet', '0003_remove_event_tarifs'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lignearticle',
            name='product',
        ),
    ]
