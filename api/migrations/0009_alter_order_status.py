# Generated by Django 4.0.5 on 2022-06-25 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_alter_order_total_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('W', 'Waiting'), ('P', 'Pending'), ('C', 'Complete'), ('F', 'Failed')], default='P', max_length=1),
        ),
    ]