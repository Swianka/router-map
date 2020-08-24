import mock
from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from data.models import Device, Link, Interface
from data.tasks import update_chassis_id, update_name, update_interfaces_via_snmp, update_links_via_snmp, \
    check_links, update_interfaces_via_netconf, update_links_via_netconf


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

    def test_update_interfaces_via_snmp(self):
        snmp_session = mock.MagicMock()
        snmp_session.get_interfaces.return_value = [('1', 'xx', 1), ('5', 'rr', 1)]
        snmp_session.get_aggregations.return_value = []
        snmp_session.get_logical_physical_connections.return_value = []

        Interface.objects.update(active=False)
        update_interfaces_via_snmp(snmp_session, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='xx', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=5, name='rr', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', speed=1, active=False, aggregate_interface=None).exists())

    def test_update_interfaces_via_snmp_with_aggregation_new(self):
        snmp_session = mock.MagicMock()
        snmp_session.get_interfaces.return_value = [('1', 'x', 1), ('2', 'y', 1), ('3', 'z', 1)]
        snmp_session.get_aggregations.return_value = [('1', '3')]
        snmp_session.get_logical_physical_connections.return_value = ['2']

        update_interfaces_via_snmp(snmp_session, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='x', aggregate_interface=None, speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=3, name='z', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())

    def test_update_interfaces_via_snmp_existing(self):
        self.interface1_device2.aggregate_interface = self.interface1_device1
        self.interface1_device2.save()
        self.interface2_device2.aggregate_interface = self.interface1_device1
        self.interface2_device2.save()

        snmp_session = mock.MagicMock()
        snmp_session.get_interfaces.return_value = [('1', 'x', 1), ('2', 'y', 1), ('3', 'z', 1)]
        snmp_session.get_aggregations.return_value = [('1', '2')]
        snmp_session.get_logical_physical_connections.return_value = ['4']

        Interface.objects.update(active=False)
        update_interfaces_via_snmp(snmp_session, self.device1)

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

    def test_update_interfaces_via_netconf(self):
        self.device1.connection_type = 'netconf'
        self.device1.save()

        netconf_session = mock.MagicMock()
        netconf_session.get_interfaces.return_value = [
            {'name': 'xx', 'number': 1, 'speed': 1, 'logical_interfaces': []},
            {'name': 'rr', 'number': 5, 'speed': 1, 'logical_interfaces': []}
        ]
        netconf_session.get_aggregations.return_value = []
        netconf_session.get_logical_physical_connections.return_value = []

        Interface.objects.update(active=False)
        update_interfaces_via_netconf(netconf_session, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='xx', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=5, name='rr', speed=1, active=True, aggregate_interface=None).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', speed=1, active=False, aggregate_interface=None).exists())

    def test_update_interfaces_via_netconf_with_aggregation(self):
        self.device1.connection_type = 'netconf'
        self.device1.save()

        netconf_session = mock.MagicMock()

        netconf_session.get_interfaces.return_value = [
            {'name': 'x', 'number': 1, 'speed': 1, 'logical_interfaces': []},
            {'name': 'y', 'number': 2, 'speed': 1, 'logical_interfaces': [{'name': 'z', 'number': 3}]},
        ]
        netconf_session.get_aggregations.return_value = [('y', 'x')]

        update_interfaces_via_netconf(netconf_session, self.device1)

        self.assertTrue(
            Interface.objects.filter(number=1, name='x', aggregate_interface=None, speed=1, active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=2, name='y', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())
        self.assertTrue(
            Interface.objects.filter(number=3, name='z', aggregate_interface=self.interface1_device1, speed=1,
                                     active=True).exists())

    @mock.patch("data.tasks.SnmpSession")
    def test_update_links_via_snmp_new(self, mock_snmp_session):
        mock_snmp_session.return_value.get_llp_neighbours.return_value = [("aa", 1, 1, True)]

        Link.objects.update(active=False)
        update_links_via_snmp(self.device2)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                                active=True).exists())

    @mock.patch("data.tasks.SnmpSession")
    def test_update_neighbours_via_snmp_existing(self, mock_snmp_session):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1)

        mock_snmp_session.return_value.get_llp_neighbours.return_value = [("aa", 1, 1, True)]

        Link.objects.update(active=False)
        update_links_via_snmp(self.device2)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=False).exists())

    @mock.patch("data.tasks.SnmpSession")
    def test_update_neighbours_via_snmp_multilink(self, mock_snmp_session):
        self.interface1_device2.aggregate_interface = self.interface1_device1
        self.interface1_device2.save()
        self.interface2_device2.aggregate_interface = self.interface1_device1
        self.interface2_device2.save()

        mock_snmp_session.return_value.get_llp_neighbours.return_value = [("aa", 2, 2, True), ("aa", 3, 3, True)]

        update_links_via_snmp(self.device2)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface3_device2, remote_interface=self.interface3_device1,
                                active=True).exists())

    @mock.patch("data.tasks.NetconfSession")
    def test_update_links_via_netconf_new(self, mock_netconf_session):
        entered = mock_netconf_session.return_value.__enter__
        entered.return_value.get_lldp_neighbours.return_value = {('x', 'aa')}
        entered.return_value.get_lldp_remote_ports_id.return_value = [1]

        Link.objects.update(active=False)
        update_links_via_netconf(self.device2)
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                                active=True).exists())

    @mock.patch("data.tasks.NetconfSession")
    def test_update_neighbours_via_netconf_existing(self, mock_netconf_session):
        Link.objects.create(local_interface=self.interface1_device2, remote_interface=self.interface1_device1)
        Link.objects.create(local_interface=self.interface2_device2, remote_interface=self.interface2_device1)

        entered = mock_netconf_session.return_value.__enter__
        entered.return_value.get_lldp_neighbours.return_value = {('x', 'aa')}
        entered.return_value.get_lldp_remote_ports_id.return_value = [1]

        Link.objects.update(active=False)
        update_links_via_netconf(self.device2)

        self.assertTrue(
            Link.objects.filter(local_interface=self.interface1_device2, remote_interface=self.interface1_device1,
                                active=True).exists())
        self.assertTrue(
            Link.objects.filter(local_interface=self.interface2_device2, remote_interface=self.interface2_device1,
                                active=False).exists())

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpSession")
    def test_check_links_new(self, mock_snmp_session):
        mock_snmp_session.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        mock_snmp_session.return_value.get_name.side_effect = ["c", "d"]
        mock_snmp_session.return_value.get_interfaces.return_value = [('10', 'p', 1)]
        mock_snmp_session.return_value.get_aggregations.return_value = []
        mock_snmp_session.return_value.get_logical_physical_connections.return_value = []
        mock_snmp_session.return_value.get_llp_neighbours.side_effect = [[("bb", 10, 10, True)],
                                                                         [("aa", 10, 10, True)]]

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
    def test_check_links_new_multilink(self, mock_snmp_session):
        mock_snmp_session.return_value.get_chassis_id.side_effect = ["aa", "bb"]
        mock_snmp_session.return_value.get_name.side_effect = ["c", "d"]
        mock_snmp_session.return_value.get_interfaces.return_value = [('10', 'p', 1), ('20', 'r', 1),
                                                                      ('30', 's', 1)]
        mock_snmp_session.return_value.get_aggregations.return_value = [('10', '20'), ('10', '30')]
        mock_snmp_session.return_value.get_logical_physical_connections.return_value = []
        mock_snmp_session.return_value.get_llp_neighbours.side_effect = [[("bb", 20, 20, True), ("bb", 30, 30, True)],
                                                                         [("aa", 20, 20, True), ("aa", 30, 30, True)]]

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
    def test_check_links_existing_inactive(self, mock_snmp_session):
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
        mock_snmp_session.return_value.get_interfaces.return_value = [('1', 'x', 1), ('2', 'y', 1), ('3', 'z', 1)]
        mock_snmp_session.return_value.get_aggregations.return_value = [('1', '2'), ('1', '3')]
        mock_snmp_session.return_value.get_logical_physical_connections.return_value = []
        mock_snmp_session.return_value.get_llp_neighbours.side_effect = [[("bb", 2, 2, True)], [("aa", 2, 2, True)]]

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
