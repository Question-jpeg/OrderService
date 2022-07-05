# Generated by Django 4.0.5 on 2022-06-29 09:42

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_alter_order_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='record_created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
