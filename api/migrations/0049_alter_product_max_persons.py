# Generated by Django 4.0.6 on 2022-07-19 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0048_remove_order_total_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='max_persons',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
