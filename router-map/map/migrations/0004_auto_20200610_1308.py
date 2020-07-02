from django.db import migrations


def forwards_func(apps, schema_editor):
    OldMap = apps.get_model('map', 'OldMap')
    NewMap = apps.get_model('map', 'NewMap')
    OldDeviceMapRelationship = apps.get_model('map', 'OldDeviceMapRelationship')
    for old_map in OldMap.objects.all():
        new_map = NewMap.objects.create(name=old_map.name,
                                        display_link_descriptions=old_map.display_link_descriptions,
                                        links_default_width=old_map.links_default_width,
                                        highlighted_links_width=old_map.highlighted_links_width,
                                        highlighted_links_range_min=old_map.highlighted_links_range_min,
                                        highlighted_links_range_max=old_map.highlighted_links_range_max)
        for device_map in OldDeviceMapRelationship.objects.filter(map=old_map.pk):
            new_map.devices.add(device_map.device, through_defaults={'point': device_map.point})
        old_map.delete()


def reverse_func(apps, schema_editor):
    OldMap = apps.get_model('map', 'OldMap')
    NewMap = apps.get_model('map', 'NewMap')
    NewDeviceMapRelationship = apps.get_model('map', 'NewDeviceMapRelationship')
    for map_to_delete in NewMap.objects.all():
        created_map = OldMap.objects.create(name=map_to_delete.name,
                                            display_link_descriptions=map_to_delete.display_link_descriptions,
                                            links_default_width=map_to_delete.links_default_width,
                                            highlighted_links_width=map_to_delete.highlighted_links_width,
                                            highlighted_links_range_min=map_to_delete.highlighted_links_range_min,
                                            highlighted_links_range_max=map_to_delete.highlighted_links_range_max)
        for device_map in NewDeviceMapRelationship.objects.filter(map=map_to_delete.pk):
            created_map.devices.add(device_map.device, through_defaults={'point': device_map.point})
        map_to_delete.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('map', '0003_auto_20200610_1308'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
