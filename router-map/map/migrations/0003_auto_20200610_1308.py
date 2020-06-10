import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('visualisation', '0001_initial'),
        ('map', '0002_auto_20200603_1018'),
    ]

    operations = [
        migrations.RenameModel('Map', 'OldMap'),
        migrations.RenameModel('DeviceMapRelationship', 'OldDeviceMapRelationship'),
        migrations.CreateModel(
            name='NewDeviceMapRelationship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point', django.contrib.gis.db.models.fields.PointField(default=None, null=True, srid=4326)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data.Device')),
            ],
        ),
        migrations.CreateModel(
            name='NewMap',
            fields=[
                ('visualisation_ptr',
                 models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                                      parent_link=True, primary_key=True, serialize=False,
                                      to='visualisation.Visualisation')),
                ('devices', models.ManyToManyField(through='map.NewDeviceMapRelationship', to='data.Device')),

            ],
            bases=('visualisation.Visualisation',),
        ),
        migrations.AddField(
            model_name='NewDeviceMapRelationship',
            name='map',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='map.NewMap'),
        ),
    ]
