from django.contrib.gis.db import models

from data.models import Device
from utils.models import Visualisation


class Diagram(Visualisation):
    devices = models.ManyToManyField(Device, through='DeviceDiagramRelationship')


class DeviceDiagramRelationship(models.Model):
    diagram = models.ForeignKey(Diagram, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    device_position_x = models.IntegerField(default=None, null=True)
    device_position_y = models.IntegerField(default=None, null=True)
