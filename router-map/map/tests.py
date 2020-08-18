import csv
import os
import tempfile

from django.contrib.auth.models import User, Permission
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from data.models import Device, Interface, Link
from map.forms import MapForm
from map.models import Map, DeviceMapRelationship


class TestHttpResponseIndex(TestCase):
    def setUp(self):
        self.map = Map.objects.create(name='Map1', pk=1)
        self.user = User.objects.create_user(username="user1", password="user1")

    def test_map_exists_not_logged_in(self):
        response = self.client.get(reverse('map:index', kwargs={'map_pk': 1}))
        self.assertRedirects(response, '/account/login/?next=/map/1/')

    def test_map_exist(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('map:index', kwargs={'map_pk': 1}))
        self.assertEqual(str(response.context['user']), 'user1')
        self.assertEqual(response.status_code, 200)

    def test_map_doesnt_exist(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('map:index', kwargs={'map_pk': 2}))
        self.assertEqual(response.status_code, 404)


class TestHttpResponsePoints(TestCase):
    def setUp(self):
        self.map = Map.objects.create(name='Map1', pk=1)
        self.user = User.objects.create_user(username="user1", password="user1")

    def test_points_not_logged_in(self):
        response = self.client.get(reverse('map:points', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 302)

    def test_points_no_exist(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('map:points', kwargs={'map_pk': 2}))
        self.assertEqual(response.status_code, 404)

    def test_points_active(self):
        self.client.login(username='user1', password='user1')
        device = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, snmp_connection=True)
        self.map.devices.add(device, through_defaults={'point': Point(1, 1)})

        json = [
            {
                "id": 1,
                "name": "a",
                "coordinates": [1, 1],
                "snmp_connection": True
            }
        ]
        response = self.client.get(reverse('map:points', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_points_nonactive(self):
        self.client.login(username='user1', password='user1')
        device = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, snmp_connection=False)
        self.map.devices.add(device, through_defaults={'point': Point(1, 1)})

        json = [
            {
                "id": 1,
                "name": "a",
                "coordinates": [1, 1],
                "snmp_connection": False
            }
        ]

        response = self.client.get(reverse('map:points', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)


class TestHttpResponseLinks(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")

        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, snmp_connection=True)
        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, snmp_connection=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

        self.map = Map.objects.create(name='Map1', pk=1)
        self.map.devices.add(self.device1, through_defaults={'point': Point(1, 1)})
        self.map.devices.add(self.device2, through_defaults={'point': Point(1, 2)})

    def test_points_not_logged_in(self):
        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 302)

    def test_points_no_exist(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 2}))
        self.assertEqual(response.status_code, 404)

    def test_lines_one_link(self):
        self.client.login(username='user1', password='user1')
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=True, pk=10)

        json = [[{"id": "10",
                  "number_of_links": 1,
                  "number_of_active_links": 1,
                  "speed": 1,
                  "device1_coordinates": [1, 2],
                  "device2_coordinates": [1, 1]
                  }]]

        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_lines_one_link_nonactive(self):
        self.client.login(username='user1', password='user1')
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False, pk=10)

        json = [[{'id': '10',
                  'number_of_links': 1,
                  "number_of_active_links": 0,
                  "speed": 1,
                  "device1_coordinates": [1, 2],
                  "device2_coordinates": [1, 1],
                  }]]
        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_lines_multilink_new_junos(self):
        self.client.login(username='user1', password='user1')
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
        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_lines_multilink_old_junos(self):
        self.client.login(username='user1', password='user1')
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
        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_lines_two_links_active(self):
        self.client.login(username='user1', password='user1')
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

        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_lines_two_links_part_active(self):
        self.client.login(username='user1', password='user1')
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
        response = self.client.get(reverse('map:lines', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)


class TestHttpResponseInactiveConnections(TestCase):
    def test_inactive_connections(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, snmp_connection=True)
        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, snmp_connection=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

        self.map = Map.objects.create(name='Map1', pk=1)
        self.map.devices.add(self.device1, through_defaults={'point': Point(1, 1)})
        self.map.devices.add(self.device2, through_defaults={'point': Point(1, 2)})

        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                            active=True)

        self.client.login(username='user1', password='user1')
        inactive_list = [{'device1_pk': 2, 'device2_pk': 1, 'description': 'b - a'}]
        response = self.client.get(reverse('map:inactive_connections', kwargs={'map_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['inactive_list'], inactive_list)


class MapFormTest(TestCase):
    def test_correct_data_only_required(self):
        data = {
            'name': 'x',
            'display_link_descriptions': True,
            'links_default_width': 5
        }
        form = MapForm(data)
        self.assertTrue(form.is_valid())

    def test_correct_data(self):

        data = {
            'name': 'x',
            'display_link_descriptions': True,
            'links_default_width': 5,
            'highlighted_links_width': 10,
            'highlighted_links_range_min': 1,
            'highlighted_links_range_max': 3
        }
        form = MapForm(data)
        self.assertTrue(form.is_valid())

    def test_error_highlighted_links_width_no_exist(self):
        data = {
            'name': 'x',
            'display_link_descriptions': True,
            'links_default_width': 5,
            'highlighted_links_range_min': 1,
            'highlighted_links_range_max': 3
        }
        form = MapForm(data)
        self.assertFalse(form.is_valid())
        self.assertEquals(form.errors['highlighted_links_width'], [u"This field is required."])

    def test_error_highlighted_links_range_max_lower_than_min(self):
        data = {
            'name': 'x',
            'display_link_descriptions': True,
            'links_default_width': 5,
            'highlighted_links_width': 10,
            'highlighted_links_range_min': 4,
            'highlighted_links_range_max': 3
        }
        form = MapForm(data)
        self.assertFalse(form.is_valid())
        self.assertEquals(form.errors['highlighted_links_range_max'],
                          [u"Ensure this value is greater than or equal to highlighted links range min."])


class TestEditMapView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.permission = Permission.objects.get(name='Can change map')
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def generate_file(self, data):
        temp_file_name = os.path.join(self.test_dir.name, 'test.csv')
        try:
            my_file = open(temp_file_name, 'w')
            wr = csv.writer(my_file)
            wr.writerow(data)
        finally:
            my_file.close()
        return my_file.name

    def test_no_permissions(self):
        self.client.login(username='user1', password='user1')
        response = self.client.post(reverse('map:create'), {'name': 'x', 'links_default_width': 3})
        self.assertEqual(response.status_code, 403)

    def test_create_map_empty(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        response = self.client.post(reverse('map:create'), {'name': 'x', 'links_default_width': 3})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Map.objects.filter(name='x').exists())

    def test_create_map_correct_file(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'snmp', 'read', '1', '1'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('map:create'), {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Map.objects.filter(name='x').exists())
            self.assertTrue(Device.objects.filter(ip_address='1.1.1.1').exists())
            m = Map.objects.get(name='x', links_default_width=3)
            d = Device.objects.get(ip_address='1.1.1.1')
            self.assertTrue(DeviceMapRelationship.objects.filter(device=d, map=m, point=Point(1, 1)).exists())

    def test_create_map_incorrect_file(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        file_path = self.generate_file(data=['1', '1.1.1', 'read'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('map:create'), {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Map.objects.filter(name='x').exists())

    def test_create_map_incorrect_file2(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'read'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('map:create'), {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Map.objects.filter(name='x').exists())

    def test_create_map_file_existing_device(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        d = Device.objects.create(name='a', ip_address="1.1.1.1", snmp_community='read', pk=1, snmp_connection=True)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'snmp', 'read', '1', '1'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('map:create'), {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Map.objects.filter(name='x').exists())
            self.assertEqual(Device.objects.all().count(), 1)
            m = Map.objects.get(name='x')
            self.assertTrue(DeviceMapRelationship.objects.filter(device=d, map=m, point=Point(1, 1)).exists())

    def test_update_map(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        self.map = Map.objects.create(name='Map1', pk=1)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'snmp', 'read', '1', '1'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('map:update', kwargs={'map_pk': 1}),
                                        {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Map.objects.filter(name='x').exists())
            self.assertEqual(Map.objects.all().count(), 1)
            self.assertTrue(Device.objects.filter(ip_address='1.1.1.1').exists())
            m = Map.objects.get(name='x')
            d = Device.objects.get(ip_address='1.1.1.1')
            self.assertTrue(DeviceMapRelationship.objects.filter(device=d, map=m, point=Point(1, 1)).exists())
