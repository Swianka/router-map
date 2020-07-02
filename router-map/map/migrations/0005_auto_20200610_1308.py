from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('map', '0004_auto_20200610_1308'),
    ]

    operations = [
        migrations.DeleteModel('OldMap'),
        migrations.DeleteModel('OldDeviceMapRelationship'),
        migrations.RenameModel('NewMap', 'Map'),
        migrations.RenameModel('NewDeviceMapRelationship', 'DeviceMapRelationship'),
    ]
