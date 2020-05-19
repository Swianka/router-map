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
