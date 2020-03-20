from django.contrib.gis.db import models

class Device(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(default='', blank=True)
    ip_address = models.GenericIPAddressField()
    snmp_community = models.TextField(default='', blank=True, help_text='string used to authenticate SNMP queries')
    snmp_connection = models.BooleanField(default=False)


class Interface(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE)
    number = models.IntegerField(help_text='number used to identify interface in MIB')
    name = models.TextField(default='', blank=True)
    speed = models.IntegerField(default=0)
    aggregate_interface = models.ForeignKey('Interface', null=True, on_delete=models.SET_NULL, related_name='aggregate')
    active = models.BooleanField(default=True)


class Link(models.Model):
    local_interface = models.ForeignKey('Interface', on_delete=models.CASCADE, related_name='local_interface',
                                        null=True)
    remote_interface = models.ForeignKey('Interface', on_delete=models.CASCADE, null=True)
    active = models.BooleanField(default=True)


class Map(models.Model):
    name = models.TextField(default='', blank=True)
    devices = models.ManyToManyField(Device, through='DeviceMapRelationship')


class Diagram(models.Model):
    name = models.TextField(default='', blank=True)
    devices = models.ManyToManyField(Device, through='DeviceDiagramRelationship')


class DeviceDiagramRelationship(models.Model):
    diagram = models.ForeignKey(Diagram, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    device_position_x = models.IntegerField(default=None, null=True)
    device_position_y = models.IntegerField(default=None, null=True)


class DeviceMapRelationship(models.Model):
    map = models.ForeignKey(Map, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    point = models.PointField(default=None, null=True)
