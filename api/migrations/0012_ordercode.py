# Generated by Django 4.0.5 on 2022-06-25 16:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_alter_order_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.PositiveSmallIntegerField(unique=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='code', to='api.order')),
            ],
        ),
    ]
