# Generated by Django 4.0.5 on 2022-06-29 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0032_alter_cartitem_price_alter_order_total_price_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
