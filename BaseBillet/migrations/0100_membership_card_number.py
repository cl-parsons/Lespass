# Generated by Django 4.2 on 2024-10-31 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('BaseBillet', '0099_alter_membership_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='card_number',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
    ]
