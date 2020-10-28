import csv
import json
import os
import tempfile

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from data.models import Device, Interface, Link
from diagram.models import Diagram, DeviceDiagramRelationship


class TestHttpResponseIndex(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.diagram = Diagram.objects.create(name='Map1', pk=1)

    def test_diagram_exists_not_logged_in(self):
        response = self.client.get(reverse('diagram:index', kwargs={'diagram_pk': 1}))
        self.assertRedirects(response, '/account/login/?next=/diagram/1/')

    def test_diagram_doesnt_exists(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('diagram:index', kwargs={'diagram_pk': 2}))
        self.assertEqual(response.status_code, 404)

    def test_diagram_exists(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('diagram:index', kwargs={'diagram_pk': 1}))
        self.assertEqual(str(response.context['user']), 'user1')
        self.assertEqual(response.status_code, 200)


class TestHttpResponseGraph(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, connection_is_active=True)
        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, connection_is_active=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

        self.diagram = Diagram.objects.create(name='Map1', pk=1)
        self.diagram.devices.add(self.device1, through_defaults={'device_position_x': 1, 'device_position_y': 1})
        self.diagram.devices.add(self.device2, through_defaults={'device_position_x': 1, 'device_position_y': 2})

    def test_not_logged_in(self):
        response = self.client.get(reverse('diagram:graph', kwargs={'diagram_pk': 1}))
        self.assertEqual(response.status_code, 302)

    def test_diagram_doesnt_exists(self):
        self.client.login(username='user1', password='user1')
        response = self.client.get(reverse('diagram:graph', kwargs={'diagram_pk': 2}))
        self.assertEqual(response.status_code, 404)

    def test_graph_one_link(self):
        self.client.login(username='user1', password='user1')
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=True, pk=10)

        json = {"devices": [
            {"id": 1, "name": "a", "coordinates": [1, 1], "connection_is_active": True},
            {"id": 2, "name": "b", "coordinates": [1, 2], "connection_is_active": True}],
            "connections": [
                {"source": 2, "target": 1, "id": "10", "number_of_links": 1,
                 "number_of_active_links": 1, "speed": 1}],
            "settings": {"display_link_descriptions": True, "links_default_width": 3, "highlighted_links_width": None,
                         "highlighted_links_range_min": None, "highlighted_links_range_max": None}
        }

        response = self.client.get(reverse('diagram:graph', kwargs={'diagram_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_graph_one_link_nonactive(self):
        self.client.login(username='user1', password='user1')
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False, pk=10)
        json = {"devices": [
            {"id": 1, "name": "a", "coordinates": [1, 1], "connection_is_active": True},
            {"id": 2, "name": "b", "coordinates": [1, 2], "connection_is_active": True}],
            "connections":
                [
                    {"source": 2, "target": 1, "id": "10", "number_of_links": 1,
                     "number_of_active_links": 0, "speed": 1}
                ],
            "settings": {"display_link_descriptions": True, "links_default_width": 3, "highlighted_links_width": None,
                         "highlighted_links_range_min": None, "highlighted_links_range_max": None}
        }
        response = self.client.get(reverse('diagram:graph', kwargs={'diagram_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)

    def test_graph_multilink(self):
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
        json = {"devices": [
            {"id": 1, "name": "a", "coordinates": [1, 1], "connection_is_active": True},
            {"id": 2, "name": "b", "coordinates": [1, 2], "connection_is_active": True}],
            "connections": [
                {"source": 2, "target": 1, "id": "11_10", "number_of_links": 2,
                 "number_of_active_links": 2, "speed": 1}],
            "settings": {"display_link_descriptions": True, "links_default_width": 3, "highlighted_links_width": None,
                         "highlighted_links_range_min": None, "highlighted_links_range_max": None}
        }
        response = self.client.get(reverse('diagram:graph', kwargs={'diagram_pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, json)


class TestHttpResponseInactiveConnections(TestCase):
    def test_inactive_connections(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, connection_is_active=True)
        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, connection_is_active=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

        self.diagram = Diagram.objects.create(name='Map1', pk=1)
        self.diagram.devices.add(self.device1, through_defaults={'device_position_x': 1, 'device_position_y': 1})
        self.diagram.devices.add(self.device2, through_defaults={'device_position_x': 1, 'device_position_y': 2})

        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=False)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                            active=True)

        self.client.login(username='user1', password='user1')
        inactive_list = [{'device1_pk': 2, 'device2_pk': 1, 'description': 'b - a'}]
        response = self.client.get(reverse('diagram:inactive_connections', args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['inactive_list'], inactive_list)


class TestEditDeviceView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.permission = Permission.objects.get(name='Can change diagram')
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
        response = self.client.post(reverse('diagram:create'), {'name': 'x', 'links_default_width': 3})
        self.assertEqual(response.status_code, 403)

    def test_create_diagram_empty(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        response = self.client.post(reverse('diagram:create'), {'name': 'x', 'links_default_width': 3})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Diagram.objects.filter(name='x').exists())

    def test_create_diagram_correct_file(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'snmp', 'read', '1', '1'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('diagram:create'),
                                        {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Diagram.objects.filter(name='x').exists())
            self.assertTrue(Device.objects.filter(ip_address='1.1.1.1').exists())
            new_diagram = Diagram.objects.get(name='x', links_default_width=3)
            d = Device.objects.get(ip_address='1.1.1.1')
            self.assertTrue(
                DeviceDiagramRelationship.objects.filter(device=d, diagram=new_diagram, device_position_x=1,
                                                         device_position_y=1).exists())

    def test_create_diagram_incorrect_file(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        file_path = self.generate_file(data=['1', '1.1.1', 'snmp', 'read'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('diagram:create'),
                                        {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Diagram.objects.filter(name='x').exists())

    def test_create_diagram_incorrect_file2(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'read'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('diagram:create'),
                                        {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Diagram.objects.filter(name='x').exists())

    def test_create_diagram_file_existing_device(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        d = Device.objects.create(name='a', ip_address="1.1.1.1", snmp_community='read', pk=1,
                                  connection_is_active=True)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'snmp', 'read', '1', '1'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('diagram:create'),
                                        {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Diagram.objects.filter(name='x').exists())
            self.assertEqual(Device.objects.all().count(), 1)
            new_diagram = Diagram.objects.get(name='x')
            self.assertTrue(
                DeviceDiagramRelationship.objects.filter(device=d, diagram=new_diagram, device_position_x=1,
                                                         device_position_y=1).exists())

    def test_update_diagram(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)
        Diagram.objects.create(name='Map1', pk=1)
        file_path = self.generate_file(data=['1', '1.1.1.1', 'snmp', 'read', '1', '1'])
        with open(file_path, "rb") as f:
            response = self.client.post(reverse('diagram:update', kwargs={'diagram_pk': 1}),
                                        {'name': 'x', 'devices': f, 'links_default_width': 3})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Diagram.objects.filter(name='x').exists())
            self.assertEqual(Diagram.objects.all().count(), 1)
            self.assertTrue(Device.objects.filter(ip_address='1.1.1.1').exists())
            new_diagram = Diagram.objects.get(name='x')
            d = Device.objects.get(ip_address='1.1.1.1')
            self.assertTrue(
                DeviceDiagramRelationship.objects.filter(device=d, diagram=new_diagram, device_position_x=1,
                                                         device_position_y=1).exists())


class TestUpdatePositionsView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.permission = Permission.objects.get(name='Can change diagram')

    def test_no_permissions(self):
        self.client.login(username='user1', password='user1')
        response = self.client.post(reverse('diagram:update_positions', args=['1']), json.dumps([]),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_update_position(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)

        diagram = Diagram.objects.create(name='Map1', pk=1)
        d1 = Device.objects.create(name='a', ip_address="1.1.1.1", snmp_community='read', pk=1,
                                   connection_is_active=True)
        d2 = Device.objects.create(name='b', ip_address="1.1.1.2", snmp_community='read', pk=2,
                                   connection_is_active=True)
        d3 = Device.objects.create(name='c', ip_address="1.1.1.3", snmp_community='read', pk=3,
                                   connection_is_active=True)
        diagram.devices.add(d1, through_defaults={'device_position_x': 10, 'device_position_y': 10})
        diagram.devices.add(d2, through_defaults={'device_position_x': 20, 'device_position_y': 20})
        diagram.devices.add(d3, through_defaults={'device_position_x': 30, 'device_position_y': 30})

        positions = [
            {'id': '1', 'x': 100, 'y': 100},
            {'id': '2', 'x': 200, 'y': 200},
            {'id': '3', 'x': 300, 'y': 300},
        ]
        response = self.client.post(reverse('diagram:update_positions', args=['1']), json.dumps(positions),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DeviceDiagramRelationship.objects.filter(diagram=diagram, device=d1, device_position_x=100,
                                                                 device_position_y=100).exists())
        self.assertTrue(DeviceDiagramRelationship.objects.filter(diagram=diagram, device=d2, device_position_x=200,
                                                                 device_position_y=200).exists())
        self.assertTrue(DeviceDiagramRelationship.objects.filter(diagram=diagram, device=d3, device_position_x=300,
                                                                 device_position_y=300).exists())
