# Generated by Django 4.0.6 on 2022-07-19 09:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0047_alter_product_max_persons'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='total_price',
        ),
    ]
