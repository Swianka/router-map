# Generated by Django 2.2 on 2020-10-05 13:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('data', '0002_auto_20200817_1650'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='chassis_id',
            field=models.CharField(blank=True, default='', max_length=31),
        ),
        migrations.AlterField(
            model_name='device',
            name='connection_type',
            field=models.CharField(choices=[('snmp', 'snmp'), ('netconf', 'netconf')], default='snmp', max_length=15),
        ),
        migrations.AlterField(
            model_name='device',
            name='name',
            field=models.CharField(blank=True, default='', max_length=127),
        ),
        migrations.AlterField(
            model_name='device',
            name='snmp_community',
            field=models.CharField(blank=True, default='', help_text='string used to authenticate SNMP queries',
                                   max_length=255),
        ),
        migrations.AlterField(
            model_name='interface',
            name='name',
            field=models.CharField(blank=True, default='', max_length=127),
        ),
    ]
