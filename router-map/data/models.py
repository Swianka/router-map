from django.contrib.gis.db import models

from utils.managers import GetOrNoneManager


class Device(models.Model):
    CONNECTION_TYPES = (
        ('snmp', 'snmp'),
        ('netconf', 'netconf'),
    )

    id = models.AutoField(primary_key=True)
    name = models.CharField(default='', max_length=127, blank=True)
    ip_address = models.GenericIPAddressField()
    chassis_id = models.CharField(default='', max_length=31, blank=True)
    snmp_community = models.CharField(default='', max_length=255, blank=True,
                                      help_text='string used to authenticate SNMP queries')
    connection_is_active = models.BooleanField(default=False)
    connection_type = models.CharField(max_length=15, choices=CONNECTION_TYPES, default='snmp')

    def __str__(self):
        return f"{self.name} (id: {self.id})"


class Interface(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE)
    number = models.IntegerField(help_text='number used to identify interface in MIB')
    name = models.CharField(default='', max_length=127, blank=True)
    speed = models.IntegerField(default=0)
    aggregate_interface = models.ForeignKey('Interface', null=True, on_delete=models.SET_NULL, related_name='aggregate')
    active = models.BooleanField(default=True)
    objects = GetOrNoneManager()


class Link(models.Model):
    local_interface = models.ForeignKey('Interface', on_delete=models.CASCADE, related_name='local_interface',
                                        null=True)
    remote_interface = models.ForeignKey('Interface', on_delete=models.CASCADE, null=True)
    active = models.BooleanField(default=True)
