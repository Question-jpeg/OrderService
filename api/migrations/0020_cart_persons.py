# Generated by Django 4.0.5 on 2022-06-28 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0019_rename_multiplicity_product_max_persons_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='persons',
            field=models.PositiveSmallIntegerField(default=6),
            preserve_default=False,
        ),
    ]