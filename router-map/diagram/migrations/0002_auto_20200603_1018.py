# Generated by Django 2.2 on 2020-06-03 08:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('diagram', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='diagram',
            name='name',
            field=models.CharField(max_length=127),
        ),
    ]
