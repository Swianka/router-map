from django.db import migrations


def forwards_func(apps, schema_editor):
    OldDiagram = apps.get_model('diagram', 'OldDiagram')
    NewDiagram = apps.get_model('diagram', 'NewDiagram')
    OldDeviceDiagramRelationship = apps.get_model('diagram', 'OldDeviceDiagramRelationship')
    for old_diagram in OldDiagram.objects.all():
        new_diagram = NewDiagram.objects.create(name=old_diagram.name,
                                                display_link_descriptions=old_diagram.display_link_descriptions,
                                                links_default_width=old_diagram.links_default_width,
                                                highlighted_links_width=old_diagram.highlighted_links_width,
                                                highlighted_links_range_min=old_diagram.highlighted_links_range_min,
                                                highlighted_links_range_max=old_diagram.highlighted_links_range_max)
        for device_diagram in OldDeviceDiagramRelationship.objects.filter(diagram=old_diagram.pk):
            new_diagram.devices.add(device_diagram.device,
                                    through_defaults={'device_position_x': device_diagram.device_position_x,
                                                      'device_position_y': device_diagram.device_position_y})
        old_diagram.delete()


def reverse_func(apps, schema_editor):
    OldDiagram = apps.get_model('diagram', 'OldDiagram')
    NewDiagram = apps.get_model('diagram', 'NewDiagram')
    NewDeviceDiagramRelationship = apps.get_model('diagram', 'NewDeviceDiagramRelationship')
    for diagram_to_delete in NewDiagram.objects.all():
        created_diagram = OldDiagram.objects.create(name=diagram_to_delete.name,
                                                    display_link_descriptions=diagram_to_delete.display_link_descriptions,
                                                    links_default_width=diagram_to_delete.links_default_width,
                                                    highlighted_links_width=diagram_to_delete.highlighted_links_width,
                                                    highlighted_links_range_min=diagram_to_delete.highlighted_links_range_min,
                                                    highlighted_links_range_max=diagram_to_delete.highlighted_links_range_max)
        for device_diagram in NewDeviceDiagramRelationship.objects.filter(diagram=diagram_to_delete.pk):
            created_diagram.devices.add(device_diagram.device,
                                        through_defaults={'device_position_x': device_diagram.device_position_x,
                                                          'device_position_y': device_diagram.device_position_y})
        diagram_to_delete.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('diagram', '0003_auto_20200610_1308'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
