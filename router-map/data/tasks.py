import logging
import re

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings
from django.db import transaction
from easysnmp import exceptions, Session
from jnpr import junos

from data import redis_client
from data.models import Device, Link, Interface

logger = logging.getLogger('maps')


class NetconfSession(junos.Device):
    def __init__(self, device):
        self.device = device
        super().__init__(host=device.ip_address, user=settings.NETCONF_USER, passwd=settings.NETCONF_PASSWORD,
                         normalize=True)

    def get_name(self):
        try:
            software_information = self.rpc.get_software_information()
            return software_information.findtext('host-name')
        except junos.exception.RpcError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")

    def get_chassis_id(self):
        try:
            lldp_local = self.rpc.get_lldp_local_info()
            return lldp_local.findtext('lldp-local-chassis-id')
        except junos.exception.RpcError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")

    def get_interfaces(self):
        try:
            interfaces_info = self.rpc.get_interface_information()
            interfaces = []

            for physical_interface in interfaces_info.findall('physical-interface'):
                physical_interface_name = physical_interface.findtext('name')
                physical_interface_speed = physical_interface.findtext('speed')
                physical_interface_number = int(physical_interface.findtext('snmp-index'))

                logical_interfaces = []
                logical_interfaces_names = []
                for logical_interface in physical_interface.findall('logical-interface'):
                    logical_interface_name = logical_interface.findtext('name')
                    logical_interface_number = logical_interface.findtext('snmp-index')
                    logical_interfaces.append({
                        'name': logical_interface_name,
                        'number': logical_interface_number,
                    })
                    logical_interfaces_names.append(logical_interface_name)
                interfaces.append({
                    'name': physical_interface_name,
                    'number': int(physical_interface_number),
                    'speed': self._normalize_speed(physical_interface_speed),
                    'logical_interfaces': logical_interfaces,
                })
            return interfaces
        except junos.exception.RpcError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            return [], {}

    def get_aggregations(self):
        try:
            lacp = self.rpc.get_lacp_interface_information()
            aggregations = []
            for aggregation in lacp.findall('lacp-interface-information'):
                aggregation_name = aggregation.findtext('.//lag-lacp-header/aggregate-name')
                for interface in aggregation.findall('lag-lacp-protocol'):
                    interface_name = interface.findtext('name')
                    aggregations.append((interface_name, aggregation_name))
            return aggregations
        except junos.exception.RpcError as e:
            if e.rpc_error['severity'] != 'warning':
                logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            return []

    def get_lldp_neighbours(self):
        try:
            lldp_neighbours = self.rpc.get_lldp_neighbors_information()
            neighbours = set()
            for neighbour in lldp_neighbours.findall('lldp-neighbor-information'):
                local_interface = neighbour.findtext('lldp-local-interface')
                remote_chassis_id = neighbour.findtext('lldp-remote-chassis-id')
                neighbours.add((local_interface, remote_chassis_id))
            return neighbours
        except junos.exception.RpcError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            return set()

    def get_lldp_remote_ports_id(self, interface):
        try:
            lldp_neighbours = self.rpc.get_lldp_interface_neighbors_information(interface_name=interface)
            remote_ports_id = []
            for neighbour in lldp_neighbours.findall('lldp-neighbor-information'):
                remote_port_id = neighbour.findtext('lldp-remote-port-id')
                remote_ports_id.append(remote_port_id)
            return remote_ports_id
        except junos.exception.RpcError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            return []

    @staticmethod
    def _normalize_speed(speed):
        if not speed or speed == "Unspecified" or speed == "Unlimited":
            return 0
        r = re.compile("([0-9]+)([a-zA-Z]+)")
        split = r.match(speed)
        speed_value = int(split.group(1))
        speed_unit = split.group(2)
        if speed_unit == 'mbps':
            return speed_value / 1000
        elif speed_unit == 'Gbps':
            return speed_value


class SnmpSession(Session):
    def __init__(self, device):
        self.device = device
        super().__init__(hostname=device.ip_address, community=device.snmp_community, version=2)

    def get_chassis_id(self):
        try:
            return self._parse_chassis_id(self.get('iso.0.8802.1.1.2.1.3.2.0').value)
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection = False
            self.device.save()

    def get_name(self):
        try:
            return self.get('iso.3.6.1.2.1.1.5.0').value
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection = False
            self.device.save()

    def get_interfaces(self):
        try:
            interface_numbers = self.bulkwalk('iso.3.6.1.2.1.2.2.1.1')
            interface_names = self.bulkwalk('iso.3.6.1.2.1.2.2.1.2')
            interface_speeds = self.bulkwalk('iso.3.6.1.2.1.31.1.1.1.15')
            return [(i.value, j.value, int(k.value) / 1000)
                    for i, j, k in zip(interface_numbers, interface_names, interface_speeds)]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection = False
            self.device.save()
            return []

    def get_aggregations(self):
        try:
            aggregate_interfaces = self.bulkwalk('iso.2.840.10006.300.43.1.2.1.1.12')
            return [(i.value, i.oid.split('.')[-1]) for i in aggregate_interfaces]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection = False
            self.device.save()
            return []

    def get_logical_physical_connections(self, port_number):
        try:
            connections = self.bulkwalk('iso.3.6.1.2.1.31.1.2.1.3.' + port_number)
            return [i.oid.split('.')[-1] for i in connections]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection = False
            self.device.save()
            return []

    def get_llp_neighbours(self):
        """
        :return: data list of neighbours info as (neighbour_chassis_id, local_interface, neighbour_interface,
                            is_neighbour_interface_id_is_number)
        """
        try:
            neighbour_chassis_ids = self.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.5')
            neighbour_interface_id_type = self.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.6')
            neighbour_interfaces = self.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.7')
            return [(self._parse_chassis_id(i.value), i.oid.split('.')[-2], j.value,
                     self._is_interface_id_number(k.value)) for i, j, k in
                    zip(neighbour_chassis_ids, neighbour_interfaces, neighbour_interface_id_type)]
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection = False
            self.device.save()
            return []

    @staticmethod
    def _is_interface_id_number(value):
        return value == '7'

    @staticmethod
    def _parse_chassis_id(value):
        return ':'.join('%02x' % ord(b) for b in value)


@periodic_task(run_every=(crontab(minute=f"*/{settings.TASK_PERIOD}")))
def check_links():
    with transaction.atomic():
        update_devices()
        update_links()
        redis_client.redis_client.set_last_update_time()


def update_devices():
    all_devices = Device.objects.only('pk', 'ip_address', 'snmp_community', 'connection_type')
    Interface.objects.update(active=False)
    for device in all_devices:
        if device.connection_type == 'snmp':
            update_device_via_snmp(device)
        elif device.connection_type == 'netconf':
            update_device_via_netconf(device)


def update_links():
    all_devices = Device.objects.only('pk', 'ip_address', 'snmp_community', 'connection_type')
    Link.objects.update(active=False)
    for device in all_devices:
        if device.connection_type == 'snmp':
            update_links_via_snmp(device)
        elif device.connection_type == 'netconf':
            update_links_via_netconf(device)


def update_device_via_snmp(device):
    snmp_session = SnmpSession(device)
    update_chassis_id(snmp_session, device)
    update_name(snmp_session, device)
    update_interfaces_via_snmp(snmp_session, device)


def update_chassis_id(session, device):
    chassis_id = session.get_chassis_id()
    if chassis_id is not None:
        device.chassis_id = chassis_id
        device.connection = True
        device.save()


def update_name(session, device):
    name = session.get_name()
    if name is None:
        device.name = str(device.ip_address)
    else:
        device.name = name
    device.save()


def update_interfaces_via_snmp(snmp_session, device):
    interfaces = snmp_session.get_interfaces()
    for number, name, speed in interfaces:
        interface, _ = Interface.objects.get_or_create(device=device, number=number)
        interface.speed = speed
        interface.name = name
        interface.aggregate_interface = None
        interface.active = True
        interface.save()
    update_aggregations_via_snmp(snmp_session, device)


def update_aggregations_via_snmp(snmp_session, device):
    aggregate_interfaces = snmp_session.get_aggregations()
    for aggregate_interface_number, interface_number in aggregate_interfaces:
        try:
            interface = get_interface_by_id(device, interface_number)
            aggregate_interface = get_interface_by_id(device, aggregate_interface_number)
            interface.aggregate_interface = aggregate_interface
            interface.save()
            logical_physical_connections = snmp_session.get_logical_physical_connections(interface_number)
        except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
            logger.warning(e)
        else:
            for connection in logical_physical_connections:
                try:
                    physical_interface = get_interface_by_id(device, connection)
                    physical_interface.aggregate_interface = aggregate_interface
                    physical_interface.save()
                except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
                    logger.warning(e)


def update_links_via_snmp(device):
    snmp_session = SnmpSession(device)
    neighbours = snmp_session.get_llp_neighbours()
    for chassis_id, interface1_number, interface2_id, interface2_id_is_number in neighbours:
        if Device.objects.filter(chassis_id=chassis_id).exists():
            remote_device = Device.objects.get(chassis_id=chassis_id)
            if device.pk > remote_device.pk:
                device1 = Device.objects.get(pk=device.pk)
                try:
                    interface1 = get_interface_by_id(device1, interface1_number)
                    if interface2_id_is_number:
                        interface2 = get_interface_by_id(remote_device, interface2_id)
                    else:
                        interface2 = get_interface_by_name(remote_device, interface2_id)
                    link, _ = Link.objects.get_or_create(local_interface=interface1,
                                                         remote_interface=interface2)
                    link.active = True
                    link.save()
                except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
                    logger.warning(e)


def update_device_via_netconf(device):
    try:
        with NetconfSession(device) as netconf_session:
            update_chassis_id(netconf_session, device)
            update_name(netconf_session, device)
            update_interfaces_via_netconf(netconf_session, device)
    except junos.exception.ConnectAuthError:
        logging.warning(f"Authentication error  (host: {device.ip_address}, pk: {device.pk})")
    except junos.exception.ConnectError:
        logger.warning(f"Connection error (host: {device.ip_address}, pk: {device.pk})")
        device.connection = False
        device.save()


def update_interfaces_via_netconf(netconf_session, device):
    interfaces = netconf_session.get_interfaces()
    interfaces_sub_layers = {}
    for interface_info in interfaces:
        logical_interface_list = []
        interface, _ = Interface.objects.get_or_create(device=device, number=interface_info['number'])
        interface.speed = interface_info['speed']
        interface.name = interface_info['name']
        interface.aggregate_interface = None
        interface.active = True
        interface.save()
        for logical_interface_info in interface_info['logical_interfaces']:
            logical_interface, _ = Interface.objects.get_or_create(device=device,
                                                                   number=logical_interface_info['number'])
            logical_interface.speed = interface_info['speed']
            logical_interface.name = logical_interface_info['name']
            logical_interface.aggregate_interface = None
            logical_interface.active = True
            logical_interface.save()
            logical_interface_list.append(logical_interface_info['name'])
        interfaces_sub_layers[interface_info['name']] = logical_interface_list
    update_aggregations_via_netconf(netconf_session, device, interfaces_sub_layers)


def update_aggregations_via_netconf(netconf_session, device, interfaces_sub_layers):
    aggregate_interfaces = netconf_session.get_aggregations()
    for (interface_name, aggregation_name) in aggregate_interfaces:
        try:
            interface = get_interface_by_name(device, interface_name)
            aggregate_interface = get_interface_by_name(device, aggregation_name)
            interface.aggregate_interface = aggregate_interface
            interface.save()
            if interfaces_sub_layers.get(interface_name) is not None:
                for logical_interface_name in interfaces_sub_layers[interface_name]:
                    logical_interface = get_interface_by_name(device, logical_interface_name)
                    logical_interface.aggregate_interface = aggregate_interface
                    logical_interface.save()
        except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
            logger.warning(e)


def update_links_via_netconf(device):
    try:
        with NetconfSession(device) as netconf_session:
            neighbours = netconf_session.get_lldp_neighbours()
            for (local_interface, remote_chassis_id) in neighbours:
                if Device.objects.filter(chassis_id=remote_chassis_id).exists():
                    remote_device = Device.objects.get(chassis_id=remote_chassis_id)
                    if device.pk > remote_device.pk:
                        device1 = Device.objects.get(pk=device.pk)
                        remote_ports_id = netconf_session.get_lldp_remote_ports_id(local_interface)
                        for remote_port_id in remote_ports_id:
                            try:
                                interface1 = get_interface_by_name(device1, local_interface)
                                interface2 = get_interface_by_id(remote_device, remote_port_id)
                                link, _ = Link.objects.get_or_create(local_interface=interface1,
                                                                     remote_interface=interface2)
                                link.active = True
                                link.save()
                            except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
                                logger.warning(e)
    except junos.exception.ConnectAuthError:
        logging.warning(f"Authentication error  (host: {device.ip_address}, pk: {device.pk})")
    except junos.exception.ConnectError:
        logger.warning(f"Connection error (host: {device.ip_address}, pk: {device.pk})")
        device.connection = False
        device.save()


def get_interface_by_id(device, interface_number):
    try:
        return Interface.objects.get(device=device, number=interface_number)
    except Interface.DoesNotExist:
        raise Interface.DoesNotExist(f"Interface number {interface_number} does not exist "
                                     f"(host: {device.ip_address}, pk: {device.pk})")
    except Interface.MultipleObjectsReturned:
        raise Interface.MultipleObjectsReturned(f"Multiple interfaces with number {interface_number} "
                                                f"(host: {device.ip_address}, pk: {device.pk})")


def get_interface_by_name(device, interface_name):
    try:
        return Interface.objects.get(device=device, name=interface_name)
    except Interface.DoesNotExist:
        raise Interface.DoesNotExist(f"Interface {interface_name} does not exist "
                                     f"(host: {device.ip_address}, pk: {device.pk})")
    except Interface.MultipleObjectsReturned:
        raise Interface.MultipleObjectsReturned(f"Multiple interfaces {interface_name} "
                                                f"(host: {device.ip_address}, pk: {device.pk})")
