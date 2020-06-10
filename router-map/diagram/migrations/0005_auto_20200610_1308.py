from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('diagram', '0004_auto_20200610_1308'),
    ]

    operations = [
        migrations.DeleteModel('OldDiagram'),
        migrations.DeleteModel('OldDeviceDiagramRelationship'),
        migrations.RenameModel('NewDiagram', 'Diagram'),
        migrations.RenameModel('NewDeviceDiagramRelationship', 'DeviceDiagramRelationship'),
    ]
