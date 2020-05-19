from django.contrib.gis.db import models

from data.models import Device
from utils.models import Visualisation


class Map(Visualisation):
    devices = models.ManyToManyField(Device, through='DeviceMapRelationship')


class DeviceMapRelationship(models.Model):
    map = models.ForeignKey(Map, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    point = models.PointField(default=None, null=True)
