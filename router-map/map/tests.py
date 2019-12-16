import csv
import os
import tempfile
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
import mock
from django.urls import reverse

from map.tasks import update_interfaces_info, update_aggregations, check_chassisid, update_links_lldp, \
    check_links, update_name, update_location
from map.models import Device, Link, Interface
from django.contrib.gis.geos import Point


class TestManagementCommand(TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def generate_file(self, location, data):
        temp_file_name = os.path.join(self.test_dir.name, 'test.csv')
        try:
            my_file = open(temp_file_name, 'w')
            wr = csv.writer(my_file)
            wr.writerow(data)
        finally:
            my_file.close()
        return my_file

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_correct_file(self):
        my_file = self.generate_file(location=False, data=['1', '1.1.1.1', 'read'])
        file_path = my_file.name
        out = StringIO()
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn("Data imported", out.getvalue())
        self.assertTrue(
            Device.objects.filter(ip_address='1.1.1.1', snmp_community='read').exists())

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_correct_file_with_location(self):
        my_file = self.generate_file(location=True, data=['1', '1.1.1.1', 'read', 1, 2])
        file_path = my_file.name
        out = StringIO()
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn("Data imported", out.getvalue())
        self.assertTrue(
            Device.objects.filter(ip_address='1.1.1.1', snmp_community='read', point=Point(1, 2)).exists())

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_correct_file_no_connection(self):
        my_file = self.generate_file(location=True, data=['1', '1.1.1.1', 'read', 1, 2])
        file_path = my_file.name
        out = StringIO()
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn("Data imported", out.getvalue())
        self.assertTrue(
            Device.objects.filter(ip_address='1.1.1.1', snmp_community='read', point=Point(1, 2)).exists())

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_incorrect_file1(self):
        my_file = self.generate_file(location=False, data=['1', '1.1.1.1'])
        file_path = my_file.name
        out = StringIO()
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn("bad data format", out.getvalue())

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_incorrect_file2(self):
        my_file = self.generate_file(location=False, data=['1', 'r', 'read'])
        file_path = my_file.name
        out = StringIO()
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn("bad data format", out.getvalue())

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_incorrect_file3(self):
        my_file = self.generate_file(location=True, data=['1', '1.1.1.1', 'read', 1, 'r'])
        file_path = my_file.name
        out = StringIO()
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn("bad data format", out.getvalue())

    @mock.patch("map.tasks.check_links", mock.MagicMock())
    def test_upload_non_existing_file(self):
        out = StringIO()
        file_path = "a.txt"
        call_command('import_router_data', file_path, stdout=out)
        self.assertIn(file_path + " doesn't exist", out.getvalue())


class TestHtpResponsePoints(TestCase):

    def test_index(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_points_active(self):
        Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, point=Point(1, 1), snmp_connection=True)

        json = {
            "type": "FeatureCollection",
            "crs":
                {
                    "type": "name",
                    "properties": {"name": "EPSG:4326"}
                },
            "features":
                [
                    {
                        "type": "Feature",
                        "properties": {'snmp_connection': True, "pk": "1"},
                        "geometry": {"type": "Point", "coordinates": [1, 1]}
                    }
                ]
        }
        response = self.client.get(reverse('points'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {
            "ip_address": "1.1.1.1",
            "name": "a",
            "snmp_connection": "active",
        }
        response2 = self.client.get(reverse('device_info', args=[1]))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)

    def test_points_nonactive(self):
        Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, point=Point(1, 1), snmp_connection=False)

        json = {
            "type": "FeatureCollection",
            "crs":
                {
                    "type": "name",
                    "properties": {"name": "EPSG:4326"}
                },
            "features":
                [
                    {
                        "type": "Feature",
                        "properties": {'snmp_connection': False, "pk": "1"},
                        "geometry": {"type": "Point", "coordinates": [1, 1]}
                    }
                ]
        }
        response = self.client.get(reverse('points'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {
            "ip_address": "1.1.1.1",
            "name": "a",
            "snmp_connection": "inactive"
        }
        response2 = self.client.get(reverse('device_info', args=[1]))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)


class TestHtpResponseLinks(TestCase):
    def setUp(self):
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, point=Point(1, 1),
                                             snmp_connection=True)

        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, point=Point(1, 2),
                                             snmp_connection=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

        self.neighbour_chassisids = {"aa": 1, "bb": 2}

    def test_lines_one_link(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=True, pk=10)

        json = [[{'id': '10',
                  'number_of_links': 1,
                  "number_of_active_links": 1,
                  "speed": 1,
                  "device1_coordinates": [1, 2],
                  "device2_coordinates": [1, 1],
                  }]]
        response = self.client.get(reverse('lines'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "interface1": "x",
                 "interface2": "x"}
        response2 = self.client.get(reverse('connection_info', args=['10']))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)

    def test_lines__one_link_nonactive(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False, pk=10)

        json = [[{'id': '10',
                  'number_of_links': 1,
                  "number_of_active_links": 0,
                  "speed": 1,
                  "device1_coordinates": [1, 2],
                  "device2_coordinates": [1, 1],
                  }]]
        response = self.client.get(reverse('lines'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 1,
                 "number_of_active_links": 0,
                 "speed": 1,
                 "interface1": "x",
                 "interface2": "x"}
        response2 = self.client.get(reverse('connection_info', args=['10']))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)

    def test_lines_multilink_new_junos(self):
        self.interface2_device1.aggregate_interface = self.interface1_device1
        self.interface2_device1.save()
        self.interface3_device1.aggregate_interface = self.interface1_device1
        self.interface3_device1.save()
        self.interface2_device2.aggregate_interface = self.interface1_device2
        self.interface2_device2.save()
        self.interface3_device2.aggregate_interface = self.interface1_device2
        self.interface3_device2.save()
        Link.objects.create(local_interface=self.interface3_device2, remote_interface=self.interface3_device1,
                            active=True, pk=10)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                            active=True, pk=11)
        json = [[{'id': '11_10',
                  'number_of_links': 2,
                  "number_of_active_links": 2,
                  "speed": 1,
                  "device1_coordinates": [1, 2],
                  "device2_coordinates": [1, 1],
                  }]]
        response = self.client.get(reverse('lines'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 2,
                 "number_of_active_links": 2,
                 "speed": 1,
                 "interface1": "z",
                 "interface2": "x"}
        response2 = self.client.get(reverse('connection_info', args=['11_10']))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)

    def test_lines_multilink_old_junos(self):
        self.interface2_device1.aggregate_interface = self.interface1_device1
        self.interface2_device1.save()
        self.interface3_device1.aggregate_interface = self.interface1_device1
        self.interface3_device1.save()
        self.interface3_device1.save()
        self.interface2_device2.aggregate_interface = self.interface1_device2
        self.interface2_device2.save()
        self.interface3_device2.aggregate_interface = self.interface1_device2
        self.interface3_device2.save()

        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface3_device1,
                            active=True, pk=10)
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface2_device1,
                            active=True, pk=11)

        json = [[{'id': '10_11',
                  'number_of_links': 2,
                  "number_of_active_links": 2,
                  "speed": 0.5,
                  "device1_coordinates": [1, 2],
                  "device2_coordinates": [1, 1],
                  }]]
        response = self.client.get(reverse('lines'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 2,
                 "number_of_active_links": 2,
                 "speed": 0.5,
                 "interface1": "x",
                 "interface2": "x"}
        response2 = self.client.get(reverse('connection_info', args=['10_11']))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)

    def test_lines_two_links_active(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=True, pk=10)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                            active=True, pk=11)

        json = [
            [
                {'id': '10',
                 'number_of_links': 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "device1_coordinates": [1, 2],
                 "device2_coordinates": [1, 1],
                 },
                {'id': '11',
                 'number_of_links': 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "device1_coordinates": [1, 2],
                 "device2_coordinates": [1, 1],
                 }

            ]
        ]

        response = self.client.get(reverse('lines'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "interface1": "x",
                 "interface2": "x"}
        json3 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "interface1": "y",
                 "interface2": "y"}
        response2 = self.client.get(reverse('connection_info', args=['10']))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)
        response3 = self.client.get(reverse('connection_info', args=['11']))
        self.assertEqual(response3.status_code, 200)
        self.assertJSONEqual(response3.content, json3)

    def test_lines_two_links_part_active(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False, pk=10)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                            active=True, pk=11)
        json = [
            [
                {'id': '10',
                 'number_of_links': 1,
                 "number_of_active_links": 0,
                 "speed": 1,
                 "device1_coordinates": [1, 2],
                 "device2_coordinates": [1, 1],
                 },
                {'id': '11',
                 'number_of_links': 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "device1_coordinates": [1, 2],
                 "device2_coordinates": [1, 1],
                 }

            ]
        ]
        response = self.client.get(reverse('lines'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

        json2 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 1,
                 "number_of_active_links": 0,
                 "speed": 1,
                 "interface1": "x",
                 "interface2": "x"}
        json3 = {"device1": "b",
                 "device2": 'a',
                 "number_of_links": 1,
                 "number_of_active_links": 1,
                 "speed": 1,
                 "interface1": "y",
                 "interface2": "y"}
        response2 = self.client.get(reverse('connection_info', args=['10']))
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, json2)

        response3 = self.client.get(reverse('connection_info', args=['11']))
        self.assertEqual(response3.status_code, 200)
        self.assertJSONEqual(response3.content, json3)

    def test_delete_inactive(self):
        self.interface1_device2.active = False
        self.interface1_device2.save()
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False)

        response = self.client.post(reverse('delete_inactive'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Interface.objects.filter(active=False).exists())
        self.assertFalse(Link.objects.filter(active=False).exists())

    def test_inactive_connections(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                            active=True)

        json = [{'device1_pk': 2, 'device2_pk': 1, 'description': 'b - a'}]
        response = self.client.get(reverse('inactive_connections'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)


class TestUpdateConnection(TestCase):
    def setUp(self):
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, point=Point(1, 1),
                                             snmp_connection=True)

        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, point=Point(1, 2),
                                             snmp_connection=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface4_device1 = Interface.objects.create(number=4, name="v", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

        self.neighbour_chassisids = {"aa": 1, "bb": 2}

    def test_check_chassisid(self):
        host_chassisid_dictionary = {}

        snmp_manager = mock.MagicMock()
        snmp_manager.get_chassisid.return_value = 'aa'

        check_chassisid(snmp_manager, self.device1, host_chassisid_dictionary)

        self.assertTrue(host_chassisid_dictionary['aa'] == 1)

    def test_update_name(self):
        snmp_manager = mock.MagicMock()
        snmp_manager.get_name.return_value = "b"

        update_name(snmp_manager, self.device1)

        self.assertTrue(
            Device.objects.filter(id=1, name='b').exists())

    def test_update_name_empty(self):
        snmp_manager = mock.MagicMock()
        snmp_manager.get_name.return_value = None

        update_name(snmp_manager, self.device1)

        self.assertTrue(
            Device.objects.filter(id=1, name=self.device1.ip_address).exists())

    def test_update_location(self):
        snmp_manager = mock.MagicMock()
        snmp_manager.get_location.return_value = "1, 2"

        update_location(snmp_manager, self.device1)
        self.assertTrue(
            Device.objects.filter(id=1, name='a', point=Point(1, 2)).exists())

    def test_update_interfaces_info_existing(self):
        snmp_manager = mock.MagicMock()
        snmp_manager.get_interfaces_info.return_value = [('1', 'xx', 1)]

        Interface.objects.update(active=False)
        update_interfaces_info(snmp_manager, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='xx', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', speed=1, active=False, aggregate_interface=None).exists())

    def test_update_aggregation_new(self):
        snmp_manager = mock.MagicMock()
        snmp_manager.get_aggregate_interfaces.return_value = [('1', '3')]
        snmp_manager.get_logical_physical_connections.return_value = ['2']

        update_aggregations(snmp_manager, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='x', aggregate_interface=None, speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=3, name='z', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())

    def test_update_interfaces_existing(self):
        self.interface1_device2.aggregate_interface = self.interface1_device1
        self.interface1_device2.save()
        self.interface2_device2.aggregate_interface = self.interface1_device1
        self.interface2_device2.save()

        snmp_manager = mock.MagicMock()
        snmp_manager.get_interfaces_info.return_value = [('1', 'x', 1), ('2', 'y', 1), ('3', 'z', 1)]
        snmp_manager.get_aggregate_interfaces.return_value = [('1', '2')]
        snmp_manager.get_logical_physical_connections.return_value = ['4']

        Interface.objects.update(active=False)
        update_interfaces_info(snmp_manager, self.device1)
        update_aggregations(snmp_manager, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='x', aggregate_interface=None, speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=3, name='z', aggregate_interface=None, speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=4, name='v', aggregate_interface=self.interface1_device1, speed=1,
                                     active=False).exists())

    def test_update_neighbours_new(self):
        snmp_manager = mock.MagicMock()
        snmp_manager.get_neighbours_info.return_value = [("aa", 1, 1)]

        Link.objects.update(active=False)
        update_links_lldp(snmp_manager, self.device2, self.neighbour_chassisids)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                                active=True).exists())

    def test_update_neighbours_existing(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1)

        snmp_manager = mock.MagicMock()
        snmp_manager.get_neighbours_info.return_value = [("aa", 1, 1)]

        Link.objects.update(active=False)
        update_links_lldp(snmp_manager, self.device2, self.neighbour_chassisids)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=False).exists())

    def test_update_neighbours_multilink(self):
        self.interface1_device2.aggregate_interface = self.interface1_device1
        self.interface1_device2.save()
        self.interface2_device2.aggregate_interface = self.interface1_device1
        self.interface2_device2.save()

        snmp_manager = mock.MagicMock()
        snmp_manager.get_neighbours_info.return_value = [("aa", 2, 2), ("aa", 3, 3)]

        update_links_lldp(snmp_manager, self.device2, self.neighbour_chassisids)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface3_device2, remote_interface=self.interface3_device1,
                                active=True).exists())

    @mock.patch("map.redis_client.redis_client", mock.MagicMock())
    @mock.patch("map.tasks.SnmpManager")
    def test_check_links_new(self, mock_snmp_manager):
        mock_snmp_manager.return_value.get_chassisid.side_effect = ["aa", "bb"]
        mock_snmp_manager.return_value.get_name.side_effect = ["c", "d"]
        mock_snmp_manager.return_value.location.side_effect = ["1 1", "1 2"]
        mock_snmp_manager.return_value.get_interfaces_info.return_value = [('10', 'p', 1)]
        mock_snmp_manager.return_value.get_aggregate_interfaces.return_value = []
        mock_snmp_manager.return_value.get_logical_physical_connections.return_value = []
        mock_snmp_manager.return_value.get_neighbours_info.side_effect = [[("bb", 10, 10)], [("aa", 10, 10)]]

        check_links()

        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device1,
                                                 active=True).exists())
        interface10_device1 = Interface.objects.get(number=10, device=self.device1)
        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device2,
                                                 active=True).exists())
        interface10_device2 = Interface.objects.get(number=10, device=self.device2)
        self.assertTrue(
            Link.objects.filter(local_interface=interface10_device2, remote_interface=interface10_device1,
                                active=True).exists())

    @mock.patch("map.redis_client.redis_client", mock.MagicMock())
    @mock.patch("map.tasks.SnmpManager")
    def test_check_links_new_multilink(self, mock_snmp_manager):
        mock_snmp_manager.return_value.get_chassisid.side_effect = ["aa", "bb"]
        mock_snmp_manager.return_value.get_name.side_effect = ["c", "d"]
        mock_snmp_manager.return_value.location.side_effect = ["1 1", "1 2"]
        mock_snmp_manager.return_value.get_interfaces_info.return_value = [('10', 'p', 1), ('20', 'r', 1),
                                                                           ('30', 's', 1)]
        mock_snmp_manager.return_value.get_aggregate_interfaces.return_value = [('10', '20'), ('10', '30')]
        mock_snmp_manager.return_value.get_logical_physical_connections.return_value = []
        mock_snmp_manager.return_value.get_neighbours_info.side_effect = [[("bb", 20, 20), ("bb", 30, 30)],
                                                                          [("aa", 20, 20), ("aa", 30, 30)]]

        check_links()

        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device1,
                                                 active=True).exists())
        interfaae10_device1 = Interface.objects.get(number=10, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=20, name='r', aggregate_interface=interfaae10_device1, device=self.device1,
                                     active=True).exists())
        interface20_device1 = Interface.objects.get(number=20, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=30, name='s', aggregate_interface=interfaae10_device1, device=self.device1,
                                     active=True).exists())
        interface30_device1 = Interface.objects.get(number=30, device=self.device1)
        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device2,
                                                 active=True).exists())
        interface10_device2 = Interface.objects.get(number=10, device=self.device2)
        self.assertTrue(
            Interface.objects.filter(number=20, name='r', aggregate_interface=interface10_device2, device=self.device2,
                                     active=True).exists())
        interface20_device2 = Interface.objects.get(number=20, device=self.device2)
        self.assertTrue(
            Interface.objects.filter(number=30, name='s', aggregate_interface=interface10_device2, device=self.device2,
                                     active=True).exists())
        interface30_device2 = Interface.objects.get(number=30, device=self.device2)
        self.assertTrue(
            Link.objects.filter(local_interface=interface20_device2, remote_interface=interface20_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=interface30_device2, remote_interface=interface30_device1,
                                active=True).exists())

    @mock.patch("map.redis_client.redis_client", mock.MagicMock())
    @mock.patch("map.tasks.SnmpManager")
    def test_check_links_existing_inactive(self, mock_snmp_manager):
        self.interface2_device1.aggregate_interface = self.interface1_device1
        self.interface2_device1.save()
        self.interface3_device1.aggregate_interface = self.interface1_device1
        self.interface3_device1.save()
        self.interface2_device2.aggregate_interface = self.interface1_device2
        self.interface2_device2.save()
        self.interface3_device2.aggregate_interface = self.interface1_device2
        self.interface3_device2.save()
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1)
        Link.objects.create(local_interface=self.interface3_device2, remote_interface=self.interface3_device1)

        mock_snmp_manager.return_value.get_chassisid.side_effect = ["aa", "bb"]
        mock_snmp_manager.return_value.get_name.side_effect = ["a", "b"]
        mock_snmp_manager.return_value.location.side_effect = ["1 1", "1 2"]
        mock_snmp_manager.return_value.get_interfaces_info.return_value = [('1', 'x', 1), ('2', 'y', 1), ('3', 'z', 1)]
        mock_snmp_manager.return_value.get_aggregate_interfaces.return_value = [('1', '2'), ('1', '3')]
        mock_snmp_manager.return_value.get_logical_physical_connections.return_value = []
        mock_snmp_manager.return_value.get_neighbours_info.side_effect = [[("bb", 2, 2)], [("aa", 2, 2)]]

        check_links()

        self.assertTrue(Interface.objects.filter(number=1, name='x', aggregate_interface=None, device=self.device1,
                                                 active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=self.interface1_device1,
                                     device=self.device1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=3, name='z', aggregate_interface=self.interface1_device1,
                                     device=self.device1, active=True).exists())
        self.assertTrue(Interface.objects.filter(number=1, name='x', aggregate_interface=None, device=self.device2,
                                                 active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=self.interface1_device2,
                                     device=self.device2, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=3, name='z', aggregate_interface=self.interface1_device2,
                                     device=self.device2, active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface3_device2, remote_interface=self.interface3_device1,
                                active=False).exists())
