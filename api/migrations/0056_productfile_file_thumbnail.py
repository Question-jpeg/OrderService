# Generated by Django 4.0.6 on 2022-08-02 07:08

from django.db import migrations
import imagekit.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0055_alter_product_max_persons'),
    ]

    operations = [
        migrations.AddField(
            model_name='productfile',
            name='file_thumbnail',
            field=imagekit.models.fields.ProcessedImageField(blank=True, null=True, upload_to='files/thumbnails'),
        ),
    ]
