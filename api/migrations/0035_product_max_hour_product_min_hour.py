# Generated by Django 4.0.5 on 2022-07-04 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0034_order_persons'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='max_hour',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='min_hour',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
