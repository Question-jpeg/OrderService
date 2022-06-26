# Generated by Django 4.0.5 on 2022-06-24 11:18

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_cart_cartitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='end_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cartitem',
            name='start_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]