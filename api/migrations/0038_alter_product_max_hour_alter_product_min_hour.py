# Generated by Django 4.0.5 on 2022-07-05 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0037_alter_productspecialinterval_common_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='max_hour',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='min_hour',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
