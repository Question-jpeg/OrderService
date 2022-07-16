# Generated by Django 4.0.5 on 2022-06-28 16:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_delete_guestprice_remove_cart_guests'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dates',
            old_name='end',
            new_name='end_datetime',
        ),
        migrations.RenameField(
            model_name='dates',
            old_name='start',
            new_name='start_datetime',
        ),
        migrations.AddField(
            model_name='dates',
            name='product',
            field=models.ForeignKey(default=6, on_delete=django.db.models.deletion.CASCADE, related_name='dates', to='api.product'),
            preserve_default=False,
        ),
    ]