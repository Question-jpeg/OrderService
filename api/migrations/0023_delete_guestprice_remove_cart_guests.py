# Generated by Django 4.0.5 on 2022-06-28 16:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0022_dates_guestprice_cart_guests'),
    ]

    operations = [
        migrations.DeleteModel(
            name='GuestPrice',
        ),
        migrations.RemoveField(
            model_name='cart',
            name='guests',
        ),
    ]
