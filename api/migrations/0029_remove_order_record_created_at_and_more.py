# Generated by Django 4.0.5 on 2022-06-29 09:44

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_order_record_created_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='record_created_at',
        ),
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
