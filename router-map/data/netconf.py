import logging
import re

from django.conf import settings
from django.db import transaction
from jnpr import junos

from data import redis_client
from data.models import Device, Link, Interface

logger = logging.getLogger('maps')


class JunosDevice(junos.Device):
    def __init__(self, device):
        self.device = device
        super().__init__(host=device.ip_address, user=settings.NETCONF_USER, passwd=settings.NETCONF_PASSWORD,
                         normalize=True)

    def get_name(self):
        return self.facts['hostname']

    def get_chassisid(self):
        try:
            lldp_local = self.rpc.get_lldp_local_info()
            return lldp_local.findtext('lldp-local-chassis-id')
        except junos.exception.RpcError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")

    def get_interfaces(self):
        try:
            interfaces_info = self.rpc.get_interface_information()
            interfaces = []
            interfaces_sub_layers = {}

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
                interfaces_sub_layers[physical_interface_name] = logical_interfaces_names
            return interfaces, interfaces_sub_layers
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
            return speed_value
        elif speed_unit == 'Gbps':
            return speed_value * 1000


def check_links():
    with transaction.atomic():
        all_hosts = Device.objects.only('pk', 'ip_address')
        host_chassisid_dictionary = {}

        Interface.objects.update(active=False)
        for host in all_hosts:
            with JunosDevice(host) as dev:
                check_chassisid(dev, host, host_chassisid_dictionary)
                update_name(dev, host)
                update_interfaces_info(dev, host)

        Link.objects.update(active=False)
        for host in all_hosts:
            with JunosDevice(host) as dev:
                update_links_lldp(dev, host, host_chassisid_dictionary)
        redis_client.redis_client.set_last_update_time()


def check_chassisid(dev, device, host_chassisid_dictionary):
    chassisid = dev.get_chassisid()
    if chassisid is not None:
        host_chassisid_dictionary[chassisid] = device.pk
        device.snmp_connection = True
        device.save()


def update_name(dev, device):
    name = dev.get_name()
    if name is None:
        device.name = str(device.ip_address)
    else:
        device.name = name
    device.save()


def update_interfaces_info(dev, device):
    interfaces, interfaces_sub_layers = dev.get_interfaces()
    for interface_info in interfaces:
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
    update_aggregations(dev, device, interfaces_sub_layers)


def update_aggregations(dev, device, interfaces_sub_layers):
    aggregate_interfaces = dev.get_aggregations()
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


def update_links_lldp(dev, device, host_chassisid_dictionary):
    neighbours = dev.get_lldp_neighbours()
    for (local_interface, remote_chassis_id) in neighbours:
        if host_chassisid_dictionary.get(remote_chassis_id) is not None:
            if device.pk > host_chassisid_dictionary[remote_chassis_id]:
                device1 = Device.objects.get(pk=device.pk)
                device2 = Device.objects.get(pk=host_chassisid_dictionary[remote_chassis_id])
                remote_ports_id = dev.get_lldp_remote_ports_id(local_interface)
                for remote_port_id in remote_ports_id:
                    try:
                        interface1 = get_interface_by_name(device1, local_interface)
                        interface2 = get_interface_by_id(device2, remote_port_id)
                        link, _ = Link.objects.get_or_create(local_interface=interface1,
                                                             remote_interface=interface2)
                        link.active = True
                        link.save()
                    except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
                        logger.warning(e)


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
