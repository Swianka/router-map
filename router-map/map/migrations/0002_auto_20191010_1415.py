# Generated by Django 2.2 on 2019-10-10 12:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('map', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Connection',
            new_name='Link',
        ),
    ]