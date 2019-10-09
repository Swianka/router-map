from django.core.management.base import BaseCommand

from map.models import Device
from map.tasks import check_connections
import csv
import os
from django.db import transaction
from django.db.utils import DataError
from django.contrib.gis.geos import Point


class Command(BaseCommand):
    help = 'Import router data from csv file into database'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='csv file with data')

    def handle(self, *args, **kwargs):
        csv_path = kwargs['file']
        if not os.path.exists(csv_path):
            self.stdout.write(f"{csv_path} doesn't exist")
            return
        with open(csv_path) as f:
            reader = csv.reader(f)
            try:
                with transaction.atomic():
                    for row in reader:
                        ip_address = row[1]
                        community = row[2]
                        if len(row) == 5:
                            Device.objects.create(ip_address=ip_address, snmp_community=community,
                                                  point=Point(float(row[3]), float(row[4])))
                        elif len(row) == 3:
                            Device.objects.create(ip_address=ip_address, snmp_community=community, point_via_snmp=True)
                self.stdout.write("Data imported")
                check_connections.apply_async()
            except (LookupError, DataError, ValueError, IndexError):
                self.stdout.write("bad data format")
