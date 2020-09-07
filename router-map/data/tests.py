import mock
from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from data.models import Device, Interface, Link
from data.tasks import update_chassis_id, update_name, update_interface_via_snmp, update_interface_via_netconf, \
    get_links_via_snmp, get_links_via_netconf, update_links, check_links


class TestHttpResponseLinksDetail(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.permission = Permission.objects.get(name='Can delete link')
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, connection=True)

        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, connection=True)

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

    def test_lines_not_logged_in(self):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=True, pk=10)
        response = self.client.get(reverse('data:connection_detail', args=['10']))
        self.assertEqual(response.status_code, 302)

    def test_lines_one_link(self):
        self.client.login(username='user1', password='user1')
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                            active=True, pk=10)
        connection = {
            "device1": 'b',
            "device2": 'a',
            "number_of_links": 1,
            "number_of_active_links": 1,
            "speed": 1,
            "interface1": 'x',
            "interface2": 'x',
        }

        response = self.client.get(reverse('data:connection_detail', args=['10']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['connection'], connection)

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

        connection = {
            "device1": 'b',
            "device2": 'a',
            "number_of_links": 2,
            "number_of_active_links": 2,
            "speed": 1,
            "interface1": 'x',
            "interface2": 'x',
        }

        response = self.client.get(reverse('data:connection_detail', args=['10_11']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['connection'], connection)

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
        connection = {
            "device1": 'b',
            "device2": 'a',
            "number_of_links": 2,
            "number_of_active_links": 2,
            "speed": 0.5,
            "interface1": 'x',
            "interface2": 'x',
        }

        response = self.client.get(reverse('data:connection_detail', args=['10_11']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['connection'], connection)

    def test_lines_delete_inactive_links_no_permission(self):
        self.client.login(username='user1', password='user1')
        response = self.client.post(reverse('data:connection_inactive_delete', args=['10_11']))
        self.assertEqual(response.status_code, 403)

    def test_lines_delete_inactive_links(self):
        self.client.login(username='user1', password='user1')
        self.user.user_permissions.add(self.permission)

        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface3_device1,
                            active=True, pk=10)
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface2_device1,
                            active=False, pk=11)

        response = self.client.post(reverse('data:connection_inactive_delete', args=['10_11']))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface3_device1,
                                active=True, pk=10).exists())
        self.assertFalse(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface2_device1,
                                active=False, pk=11).exists())


class TestUpdateConnection(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, connection=True,
                                             chassis_id='aa')
        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, connection=True,
                                             chassis_id='bb')

        self.interface1_device1 = Interface.objects.create(number=1, name="x", speed=1, device=self.device1)
        self.interface2_device1 = Interface.objects.create(number=2, name="y", speed=1, device=self.device1)
        self.interface3_device1 = Interface.objects.create(number=3, name="z", speed=1, device=self.device1)
        self.interface4_device1 = Interface.objects.create(number=4, name="v", speed=1, device=self.device1)
        self.interface1_device2 = Interface.objects.create(number=1, name="x", speed=1, device=self.device2)
        self.interface2_device2 = Interface.objects.create(number=2, name="y", speed=1, device=self.device2)
        self.interface3_device2 = Interface.objects.create(number=3, name="z", speed=1, device=self.device2)

    def test_update_chassis_id(self):
        session = mock.MagicMock()
        session.get_chassis_id.return_value = 'aa'

        update_chassis_id(session, self.device1)

        self.assertTrue(Device.objects.filter(id=1, chassis_id='aa').exists())

    def test_update_name(self):
        session = mock.MagicMock()
        session.get_name.return_value = "b"

        update_name(session, self.device1)

        self.assertTrue(Device.objects.filter(id=1, name='b').exists())

    def test_update_name_empty(self):
        session = mock.MagicMock()
        session.get_name.return_value = None

        update_name(session, self.device1)

        self.assertTrue(Device.objects.filter(id=1, name=self.device1.ip_address).exists())

    def test_update_interface_via_snmp(self):
        snmp_session = mock.MagicMock()
        snmp_session.get_interface.return_value = {'name': 'xx', 'number': 1, 'speed': 1}
        snmp_session.get_aggregate_interface.return_value = None

        Interface.objects.update(active=False)
        update_interface_via_snmp(snmp_session, 1, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='xx', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', speed=1, active=False, aggregate_interface=None).exists())

    def test_update_interface_via_snmp_with_aggregation(self):
        snmp_session = mock.MagicMock()
        snmp_session.get_interface.side_effect = [{'name': 'x', 'number': 1, 'speed': 1},
                                                  {'name': 'y', 'number': 2, 'speed': 1}]
        snmp_session.get_aggregate_interface.return_value = 2

        Interface.objects.update(active=False)
        update_interface_via_snmp(snmp_session, 1, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='x', aggregate_interface=self.interface2_device1,
                                     speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=None, speed=1,
                                     active=True).exists())

    def test_update_interface_via_netconf(self):
        self.device1.connection_type = 'netconf'
        self.device1.save()

        netconf_session = mock.MagicMock()
        netconf_session.get_interface.return_value = {'name': 'xx', 'number': 1, 'speed': 1}

        Interface.objects.update(active=False)
        update_interface_via_netconf(netconf_session, 'xx', None, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='xx', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', speed=1, active=False, aggregate_interface=None).exists())

    def test_update_interfaces_via_netconf_with_aggregation(self):
        self.device1.connection_type = 'netconf'
        self.device1.save()

        netconf_session = mock.MagicMock()
        netconf_session.get_interface.side_effect = [{'name': 'x', 'number': 1, 'speed': 1},
                                                     {'name': 'y', 'number': 2, 'speed': 1}]

        Interface.objects.update(active=False)
        update_interface_via_netconf(netconf_session, 'x', 'y', self.device1)

        self.assertTrue(Interface.objects.filter(number=1, name='x', aggregate_interface=self.interface2_device1,
                                                 speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=None, speed=1, active=True).exists())

    def test_get_links_via_snmp(self):
        snmp_session = mock.MagicMock()
        snmp_session.get_lldp_neighbours.return_value = [{'remote_chassis_id': "aa", 'local_interface': 1,
                                                          'remote_interface': 1, 'is_remote_interface_is_number': True}]
        snmp_session.get_interface.return_value = {'name': 'xx', 'number': 1, 'speed': 1}
        snmp_session.get_aggregate_interface.return_value = None

        Interface.objects.update(active=False)
        links = [{'local_interface_id': self.interface1_device2.id,
                  'remote_device_id': self.device1.id,
                  'remote_interface': 1,
                  'is_remote_interface_is_number': True}]

        self.assertEqual(get_links_via_snmp(snmp_session, self.device2), links)

    def test_get_links_via_snmp_multilink(self):
        snmp_session = mock.MagicMock()
        snmp_session.get_lldp_neighbours.return_value = [{'remote_chassis_id': "aa", 'local_interface': 1,
                                                          'remote_interface': 1, 'is_remote_interface_is_number': True},
                                                         {'remote_chassis_id': "aa", 'local_interface': 2,
                                                          'remote_interface': 2, 'is_remote_interface_is_number': True}
                                                         ]
        snmp_session.get_interface.side_effect = [{'name': 'x', 'number': 1, 'speed': 1},
                                                  {'name': 'z', 'number': 3, 'speed': 1},
                                                  {'name': 'y', 'number': 2, 'speed': 1},
                                                  {'name': 'z', 'number': 3, 'speed': 1}]
        snmp_session.get_aggregate_interface.return_value = 3

        Interface.objects.update(active=False)
        links = [{'local_interface_id': self.interface1_device2.id,
                  'remote_device_id': self.device1.id,
                  'remote_interface': 1,
                  'is_remote_interface_is_number': True},
                 {'local_interface_id': self.interface2_device2.id,
                  'remote_device_id': self.device1.id,
                  'remote_interface': 2,
                  'is_remote_interface_is_number': True}]

        self.assertEqual(get_links_via_snmp(snmp_session, self.device2), links)

    def test_get_links_via_netconf_new(self):
        self.device1.connection_type = 'netconf'
        self.device1.save()

        netconf_session = mock.MagicMock()
        netconf_session.get_lldp_neighbours.return_value = [('x', 'aa')]
        netconf_session.get_lldp_neighbour_details.return_value = [{'local_interface': 'x', 'parent_interface': None,
                                                                    'remote_chassis_id': 'aa',
                                                                    'remote_interface_number': 1}]
        netconf_session.get_interface.return_value = {'name': 'x', 'number': 1, 'speed': 1}

        Interface.objects.update(active=False)
        links = [{'local_interface_id': self.interface1_device2.id,
                  'remote_device_id': self.device1.id,
                  'remote_interface': 1,
                  'is_remote_interface_is_number': True}]

        self.assertEqual(get_links_via_netconf(netconf_session, self.device2), links)

    def test_get_links_via_netconf_multilink(self):
        self.device1.connection_type = 'netconf'
        self.device1.save()

        netconf_session = mock.MagicMock()
        netconf_session.get_lldp_neighbours.return_value = [('x', 'aa'), ('y', 'aa')]
        netconf_session.get_lldp_neighbour_details.side_effect = [[{'local_interface': 'x', 'parent_interface': None,
                                                                    'remote_chassis_id': 'aa',
                                                                    'remote_interface_number': 1}],
                                                                  [{'local_interface': 'y', 'parent_interface': None,
                                                                    'remote_chassis_id': 'aa',
                                                                    'remote_interface_number': 2}]]
        netconf_session.get_interface.side_effect = [{'name': 'x', 'number': 1, 'speed': 1},
                                                     {'name': 'y', 'number': 2, 'speed': 1}]

        Interface.objects.update(active=False)
        links = [{'local_interface_id': self.interface1_device2.id,
                  'remote_device_id': self.device1.id,
                  'remote_interface': 1,
                  'is_remote_interface_is_number': True},
                 {'local_interface_id': self.interface2_device2.id,
                  'remote_device_id': self.device1.id,
                  'remote_interface': 2,
                  'is_remote_interface_is_number': True}]

        self.assertEqual(get_links_via_netconf(netconf_session, self.device2), links)

    def test_update_links(self):
        neighbours_list = [{'local_interface_id': self.interface1_device2.id,
                            'remote_device_id': self.device1.id,
                            'remote_interface': 1,
                            'is_remote_interface_is_number': True},
                           {'local_interface_id': self.interface2_device2.id,
                            'remote_device_id': self.device1.id,
                            'remote_interface': 2,
                            'is_remote_interface_is_number': True}
                           ]
        update_links(neighbours_list)
        self.assertTrue(Link.objects.filter(local_interface=self.interface1_device2,
                                            remote_interface=self.interface1_device1, active=True).exists())
        self.assertTrue(Link.objects.filter(local_interface=self.interface2_device2,
                                            remote_interface=self.interface2_device1, active=True).exists())

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpSession")
    def test_check_links_new_snmp(self, mock_snmp_session):
        mock_snmp_session.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        mock_snmp_session.return_value.get_name.side_effect = ["a", "b"]
        mock_snmp_session.return_value.get_interface.return_value = {'name': 'p', 'number': 10, 'speed': 1}
        mock_snmp_session.return_value.get_aggregate_interface.return_value = None
        mock_snmp_session.return_value.get_lldp_neighbours.side_effect = [
            [{'remote_chassis_id': "bb", 'local_interface': 10,
              'remote_interface': 10, 'is_remote_interface_is_number': True}],
            [{'remote_chassis_id': "aa", 'local_interface': 10,
              'remote_interface': 10, 'is_remote_interface_is_number': True}]]

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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpSession")
    def test_check_links_new_multilink_snmp(self, mock_snmp_session):
        mock_snmp_session.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        mock_snmp_session.return_value.get_name.side_effect = ["a", "b"]
        mock_snmp_session.return_value.get_interface.side_effect = [{'name': 'r', 'number': 20, 'speed': 1},
                                                                    {'name': 'p', 'number': 10, 'speed': 1},
                                                                    {'name': 's', 'number': 30, 'speed': 1},
                                                                    {'name': 'r', 'number': 20, 'speed': 1},
                                                                    {'name': 'p', 'number': 10, 'speed': 1},
                                                                    {'name': 's', 'number': 30, 'speed': 1}, ]
        mock_snmp_session.return_value.get_aggregate_interface.side_effect = [10, 10, 10, 10]
        mock_snmp_session.return_value.get_lldp_neighbours.side_effect = [
            [{'remote_chassis_id': "bb", 'local_interface': 20,
              'remote_interface': 20, 'is_remote_interface_is_number': True},
             {'remote_chassis_id': "bb", 'local_interface': 30,
              'remote_interface': 30, 'is_remote_interface_is_number': True}],
            [{'remote_chassis_id': "aa", 'local_interface': 20,
              'remote_interface': 20, 'is_remote_interface_is_number': True},
             {'remote_chassis_id': "aa", 'local_interface': 30,
              'remote_interface': 30, 'is_remote_interface_is_number': True}]]

        check_links()

        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device1,
                                                 active=True).exists())
        interface10_device1 = Interface.objects.get(number=10, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=20, name='r', aggregate_interface=interface10_device1, device=self.device1,
                                     active=True).exists())
        interface20_device1 = Interface.objects.get(number=20, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=30, name='s', aggregate_interface=interface10_device1, device=self.device1,
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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpSession")
    def test_check_links_existing_inactive_snmp(self, mock_snmp_session):
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

        mock_snmp_session.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        mock_snmp_session.return_value.get_name.side_effect = ["a", "b"]
        mock_snmp_session.return_value.get_interface.side_effect = [{'name': 'y', 'number': 2, 'speed': 1},
                                                                    {'name': 'x', 'number': 1, 'speed': 1},
                                                                    {'name': 'y', 'number': 2, 'speed': 1},
                                                                    {'name': 'x', 'number': 1, 'speed': 1}]
        mock_snmp_session.return_value.get_aggregate_interface.side_effect = [1, 1, 1, 1]
        mock_snmp_session.return_value.get_lldp_neighbours.side_effect = [
            [{'remote_chassis_id': "bb", 'local_interface': 2,
              'remote_interface': 2, 'is_remote_interface_is_number': True}],
            [{'remote_chassis_id': "aa", 'local_interface': 2,
              'remote_interface': 2, 'is_remote_interface_is_number': True}]]

        check_links()

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface3_device2, remote_interface=self.interface3_device1,
                                active=False).exists())

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.NetconfSession")
    def test_check_links_new_netconf(self, mock_netconf_session):
        self.device1.connection_type = 'netconf'
        self.device1.save()
        self.device2.connection_type = 'netconf'
        self.device2.save()

        entered = mock_netconf_session.return_value.__enter__
        entered.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        entered.return_value.get_name.side_effect = ["a", "b"]
        entered.return_value.get_interface.return_value = {'name': 'p', 'number': 10, 'speed': 1}
        entered.return_value.get_lldp_neighbours.side_effect = [[('p', 'bb')],
                                                                [('p', 'aa')]]
        entered.return_value.get_lldp_neighbour_details.side_effect = [
            [{'local_interface': 'p', 'parent_interface': None, 'remote_chassis_id': 'bb',
              'remote_interface_number': 10}],
            [{'local_interface': 'p', 'parent_interface': None, 'remote_chassis_id': 'aa',
              'remote_interface_number': 10}]]

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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.NetconfSession")
    def test_check_links_new_multilink_netconf(self, mock_netconf_session):
        self.device1.connection_type = 'netconf'
        self.device1.save()
        self.device2.connection_type = 'netconf'
        self.device2.save()

        entered = mock_netconf_session.return_value.__enter__
        entered.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        entered.return_value.get_name.side_effect = ["a", "b"]
        entered.return_value.get_interface.side_effect = [{'name': 'r', 'number': 20, 'speed': 1},
                                                          {'name': 'p', 'number': 10, 'speed': 1},
                                                          {'name': 's', 'number': 30, 'speed': 1},
                                                          {'name': 'r', 'number': 20, 'speed': 1},
                                                          {'name': 'p', 'number': 10, 'speed': 1},
                                                          {'name': 's', 'number': 30, 'speed': 1}]
        entered.return_value.get_lldp_neighbours.side_effect = [[('r', 'bb'), ('s', 'bb')],
                                                                [('r', 'aa'), ('s', 'aa')]]

        entered.return_value.get_lldp_neighbour_details.side_effect = [
            [{'local_interface': 'r', 'parent_interface': 'p', 'remote_chassis_id': 'bb',
              'remote_interface_number': 20}],
            [{'local_interface': 's', 'parent_interface': 'p', 'remote_chassis_id': 'bb',
              'remote_interface_number': 30}],
            [{'local_interface': 'r', 'parent_interface': 'p', 'remote_chassis_id': 'aa',
              'remote_interface_number': 20}],
            [{'local_interface': 's', 'parent_interface': 'p', 'remote_chassis_id': 'aa',
              'remote_interface_number': 30}]]

        check_links()

        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device1,
                                                 active=True).exists())
        interface10_device1 = Interface.objects.get(number=10, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=20, name='r', aggregate_interface=interface10_device1, device=self.device1,
                                     active=True).exists())
        interface20_device1 = Interface.objects.get(number=20, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=30, name='s', aggregate_interface=interface10_device1, device=self.device1,
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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpSession")
    @mock.patch("data.tasks.NetconfSession")
    def test_check_links_new_multilink_snmp_and_netconf(self, mock_netconf_session, mock_snmp_session):
        self.device2.connection_type = 'netconf'
        self.device2.save()

        entered = mock_netconf_session.return_value.__enter__
        entered.return_value.get_chassis_id.return_value = "bb"
        entered.return_value.get_name.return_value = "b"
        entered.return_value.get_interface.side_effect = [{'name': 'r', 'number': 20, 'speed': 1},
                                                          {'name': 'p', 'number': 10, 'speed': 1},
                                                          {'name': 's', 'number': 30, 'speed': 1}]
        entered.return_value.get_lldp_neighbours.return_value = [('r', 'aa'), ('s', 'aa')]

        entered.return_value.get_lldp_neighbour_details.side_effect = [
            [{'local_interface': 'r', 'parent_interface': 'p', 'remote_chassis_id': 'aa',
              'remote_interface_number': 20}],
            [{'local_interface': 's', 'parent_interface': 'p', 'remote_chassis_id': 'aa',
              'remote_interface_number': 30}]]

        mock_snmp_session.return_value.get_chassis_id.return_value = "aa"
        mock_snmp_session.return_value.get_name.return_value = "a"
        mock_snmp_session.return_value.get_interface.side_effect = [{'name': 'r', 'number': 20, 'speed': 1},
                                                                    {'name': 'p', 'number': 10, 'speed': 1},
                                                                    {'name': 's', 'number': 30, 'speed': 1}]
        mock_snmp_session.return_value.get_aggregate_interface.side_effect = [10, 10]
        mock_snmp_session.return_value.get_lldp_neighbours.return_value = [
            {'remote_chassis_id': "bb", 'local_interface': 20,
             'remote_interface': 20, 'is_remote_interface_is_number': True},
            {'remote_chassis_id': "bb", 'local_interface': 30,
             'remote_interface': 30, 'is_remote_interface_is_number': True}]

        check_links()

        self.assertTrue(Interface.objects.filter(number=10, name='p', aggregate_interface=None, device=self.device1,
                                                 active=True).exists())
        interface10_device1 = Interface.objects.get(number=10, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=20, name='r', aggregate_interface=interface10_device1, device=self.device1,
                                     active=True).exists())
        interface20_device1 = Interface.objects.get(number=20, device=self.device1)
        self.assertTrue(
            Interface.objects.filter(number=30, name='s', aggregate_interface=interface10_device1, device=self.device1,
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
