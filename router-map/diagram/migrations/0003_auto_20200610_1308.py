import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('visualisation', '0001_initial'),
        ('diagram', '0002_auto_20200603_1018'),
    ]
    operations = [
        migrations.RenameModel('Diagram', 'OldDiagram'),
        migrations.RenameModel('DeviceDiagramRelationship', 'OldDeviceDiagramRelationship'),
        migrations.CreateModel(
            name='NewDeviceDiagramRelationship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_position_x', models.IntegerField(default=None, null=True)),
                ('device_position_y', models.IntegerField(default=None, null=True)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data.Device')),
            ],
        ),
        migrations.CreateModel(
            name='NewDiagram',
            fields=[
                ('visualisation_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                                      parent_link=True, primary_key=True, serialize=False,
                                      to='visualisation.Visualisation')),
                ('devices', models.ManyToManyField(through='diagram.NewDeviceDiagramRelationship', to='data.Device')),

            ],
            bases=('visualisation.Visualisation',),
        ),
        migrations.AddField(
            model_name='NewDeviceDiagramRelationship',
            name='diagram',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='diagram.NewDiagram'),
        ),
    ]
