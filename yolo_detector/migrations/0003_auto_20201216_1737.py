# Generated by Django 3.1.4 on 2020-12-16 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('yolo_detector', '0002_tblproduct'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tblproduct',
            name='quantity',
            field=models.IntegerField(verbose_name=11),
        ),
    ]
