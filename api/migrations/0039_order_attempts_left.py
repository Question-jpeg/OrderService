# Generated by Django 4.0.5 on 2022-07-05 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0038_alter_product_max_hour_alter_product_min_hour'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='attempts_left',
            field=models.SmallIntegerField(default=3),
            preserve_default=False,
        ),
    ]
