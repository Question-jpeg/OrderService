# Generated by Django 4.0.6 on 2022-07-17 10:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0044_cartitem_quantity_product_quantity_multiplier'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='quantity_multiplier',
        ),
    ]
