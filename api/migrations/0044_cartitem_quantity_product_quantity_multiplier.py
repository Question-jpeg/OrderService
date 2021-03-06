# Generated by Django 4.0.6 on 2022-07-17 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0043_remove_userpushnotificationtoken_username_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='quantity',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='product',
            name='quantity_multiplier',
            field=models.BooleanField(default=False),
        ),
    ]
