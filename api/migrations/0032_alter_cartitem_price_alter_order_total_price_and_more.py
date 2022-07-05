# Generated by Django 4.0.5 on 2022-06-29 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_cartitem_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='price',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_price',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='total_price',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='product',
            name='unit_price',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='productspecialinterval',
            name='additional_price_per_unit',
            field=models.IntegerField(),
        ),
    ]
