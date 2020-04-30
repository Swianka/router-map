import mock
from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from data.models import Device, Link, Interface
from data.tasks import update_interfaces_info, update_aggregations, check_chassisid, update_links_lldp, \
    check_links, update_name


class TestHtpResponseLinksDetail(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="user1")
        self.permission = Permission.objects.get(name='Can delete link')
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, snmp_connection=True)

        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, snmp_connection=True)

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
        self.device1 = Device.objects.create(name='a', ip_address="1.1.1.1", pk=1, snmp_connection=True)
        self.device2 = Device.objects.create(name='b', ip_address="1.1.1.2", pk=2, snmp_connection=True)

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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpManager")
    def test_check_links_new(self, mock_snmp_manager):
        mock_snmp_manager.return_value.get_chassisid.side_effect = ["aa", "bb"]
        mock_snmp_manager.return_value.get_name.side_effect = ["c", "d"]
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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpManager")
    def test_check_links_new_multilink(self, mock_snmp_manager):
        mock_snmp_manager.return_value.get_chassisid.side_effect = ["aa", "bb"]
        mock_snmp_manager.return_value.get_name.side_effect = ["c", "d"]
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

    @mock.patch("data.redis_client.redis_client", mock.MagicMock())
    @mock.patch("data.tasks.SnmpManager")
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
