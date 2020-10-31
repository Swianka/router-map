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


def netconf_exception_handler(default=None):
    def decorator(func):
        def inner_function(*args, **kwargs):
            device = args[0].device
            try:
                return func(*args, **kwargs)
            except junos.exception.RpcError as e:
                logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
                return default

        return inner_function

    return decorator


class NetconfSession(junos.Device):
    def __init__(self, device):
        self.device = device
        super().__init__(host=device.ip_address, user=settings.NETCONF_USER, passwd=settings.NETCONF_PASSWORD,
                         normalize=True)

    @netconf_exception_handler()
    def get_name(self):
        return self.facts["hostname"]

    @netconf_exception_handler()
    def get_chassis_id(self):
        lldp_local = self.rpc.get_lldp_local_info()
        return lldp_local.findtext('lldp-local-chassis-id')

    @netconf_exception_handler()
    def get_interface(self, interface_name):
        interface_info = self.rpc.get_interface_information(interface_name=interface_name)
        interface_speed = interface_info.findtext('./physical-interface/speed')
        interface_number = interface_info.findtext('./physical-interface/snmp-index')
        if interface_number:
            return {
                'name': interface_name,
                'number': int(interface_number),
                'speed': self._normalize_speed(interface_speed)
            }
        else:
            logger.warning(f"unexpected format of rpc response "
                           f"(host: {self.device.ip_address}, pk: {self.device.pk})")

    @netconf_exception_handler(default=set())
    def get_lldp_neighbours(self):
        lldp_neighbours = self.rpc.get_lldp_neighbors_information()
        neighbours = set()
        for neighbour in lldp_neighbours.findall('lldp-neighbor-information'):
            local_interface = neighbour.findtext('lldp-local-port-id')
            if not local_interface:
                local_interface = neighbour.findtext('lldp-local-interface')
            remote_chassis_id = neighbour.findtext('lldp-remote-chassis-id')
            if local_interface and remote_chassis_id:
                neighbours.add((local_interface, remote_chassis_id))
        return neighbours

    @netconf_exception_handler(default=[])
    def get_lldp_neighbour_details(self, interface):
        lldp_neighbours = self.rpc.get_lldp_interface_neighbors(interface_device=interface)
        neighbour_details = []
        for neighbour in lldp_neighbours.findall('lldp-neighbor-information'):
            local_interface = neighbour.findtext('lldp-local-interface')
            parent_interface = neighbour.findtext('lldp-local-parent-interface-name')
            remote_chassis_id = neighbour.findtext('lldp-remote-chassis-id')
            remote_interface_number = neighbour.findtext('lldp-remote-port-id')
            neighbour_details.append({
                'local_interface': local_interface,
                'parent_interface': None if parent_interface == '-' else parent_interface,
                'remote_chassis_id': remote_chassis_id,
                'remote_interface_number': remote_interface_number
            })
        return neighbour_details

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


def snmp_exception_handler(default=None):
    def decorator(func):
        def inner_function(*args, **kwargs):
            device = args[0].device
            try:
                return func(*args, **kwargs)
            except exceptions.EasySNMPError as e:
                logger.warning(f"{e} (host: {device.ip_address}, pk: {device.pk})")
                device.connection_is_active = False
                device.save()
                return default

        return inner_function

    return decorator


class SnmpSession(Session):
    def __init__(self, device):
        self.device = device
        super().__init__(hostname=device.ip_address, community=device.snmp_community, version=2)

    @snmp_exception_handler()
    def get_chassis_id(self):
        return self._parse_chassis_id(self.get('iso.0.8802.1.1.2.1.3.2.0').value)

    @snmp_exception_handler()
    def get_name(self):
        try:
            return self.get('iso.3.6.1.2.1.1.5.0').value
        except exceptions.EasySNMPError as e:
            logger.warning(f"{e} (host: {self.device.ip_address}, pk: {self.device.pk})")
            self.device.connection_is_active = False
            self.device.save()

    @snmp_exception_handler()
    def get_interface(self, interface_number):
        interface_name = self.get('iso.3.6.1.2.1.2.2.1.2.' + interface_number)
        interface_speed = self.get('iso.3.6.1.2.1.31.1.1.1.15.' + interface_number)
        if interface_name.value != 'NOSUCHINSTANCE':
            return {
                'name': interface_name.value,
                'number': interface_number,
                'speed': int(interface_speed.value) / 1000
            }
        else:
            logger.warning(f"Interface number {interface_number} does not exist "
                           f"(host: {self.device.ip_address}, pk: {self.device.pk})")

    @snmp_exception_handler()
    def get_physical_interface_number(self, logical_interface_number):
        connections = self.bulkwalk('iso.3.6.1.2.1.31.1.2.1.3.' + logical_interface_number)
        return [i.oid.split('.')[-1] for i in connections]

    @snmp_exception_handler(default=[])
    def get_aggregations(self):
        aggregate_interfaces = self.bulkwalk('iso.2.840.10006.300.43.1.2.1.1.12')
        return [{
            'aggregate_interface': i.value,
            'logical_interface': i.oid.split('.')[-1]
        }
            for i in aggregate_interfaces]

    @snmp_exception_handler(default=[])
    def get_lldp_neighbours(self):
        neighbour_chassis_ids = self.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.5')
        neighbour_interface_type = self.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.6')
        neighbour_interfaces = self.bulkwalk('iso.0.8802.1.1.2.1.4.1.1.7')
        return [{
            'remote_chassis_id': self._parse_chassis_id(i.value),
            'local_interface': i.oid.split('.')[-2],
            'remote_interface': j.value,
            'is_remote_interface_is_number': self._is_interface_number(k.value)
        }
            for i, j, k in
            zip(neighbour_chassis_ids, neighbour_interfaces, neighbour_interface_type)]

    @staticmethod
    def _is_interface_number(value):
        return value == '7'

    @staticmethod
    def _parse_chassis_id(value):
        return ':'.join('%02x' % ord(b) for b in value)


@periodic_task(run_every=(crontab(minute=f"*/{settings.TASK_PERIOD}")))
def check_links():
    with transaction.atomic():
        all_devices = Device.objects.only('id', 'ip_address', 'snmp_community', 'connection_type')
        Interface.objects.update(active=False)
        neighbours = []
        for device in all_devices:
            if device.connection_type == 'snmp':
                neighbours_list = update_device_via_snmp(device)
            elif device.connection_type == 'netconf':
                neighbours_list = update_device_via_netconf(device)
            neighbours.extend(neighbours_list)
        Link.objects.update(active=False)
        update_links(neighbours)
        redis_client.redis_client.set_last_update_time()


def update_device_via_snmp(device):
    snmp_session = SnmpSession(device)
    update_chassis_id(snmp_session, device)
    update_name(snmp_session, device)
    return get_links_via_snmp(snmp_session, device)


def update_chassis_id(session, device):
    chassis_id = session.get_chassis_id()
    if chassis_id is not None:
        device.chassis_id = chassis_id
        device.connection_is_active = True
        device.save()


def update_name(session, device):
    name = session.get_name()
    if name is None:
        device.name = str(device.ip_address)
    else:
        device.name = name
    device.save()


def get_active_or_update_interface_via_snmp(snmp_session, interface_number, device):
    interface = Interface.objects.get_or_none(device=device, number=interface_number, active=True)
    if interface is not None:
        return interface.id
    else:
        interface_details = snmp_session.get_interface(interface_number)
        if interface_details:
            interface, _ = Interface.objects.get_or_create(device=device, number=interface_number)
            interface.active = True
            interface.speed = interface_details['speed']
            interface.name = interface_details['name']
            interface.aggregate_interface = None
            interface.save()
            return interface.id


def update_aggregations_via_snmp(snmp_session, device):
    aggregations = snmp_session.get_aggregations()
    for aggregation in aggregations:
        aggregate_interface_number = aggregation['aggregate_interface']
        logical_interface_number = aggregation['logical_interface']
        physical_interface_numbers = snmp_session.get_physical_interface_number(logical_interface_number)
        for physical_interface_number in physical_interface_numbers:
            physical_interface = Interface.objects.get_or_none(device=device, number=physical_interface_number,
                                                               active=True)
            if physical_interface is not None:
                aggregate_interface = Interface.objects.get_or_none(device=device, number=aggregate_interface_number,
                                                                    active=True)
                if aggregate_interface is None:
                    aggregate_interface_detail = snmp_session.get_interface(aggregate_interface_number)
                    aggregate_interface, _ = Interface.objects.get_or_create(device=device,
                                                                             number=aggregate_interface_number)
                    aggregate_interface.active = True
                    aggregate_interface.name = aggregate_interface_detail['name']
                    aggregate_interface.speed = aggregate_interface_detail['speed']
                    aggregate_interface.save()
                physical_interface.aggregate_interface = aggregate_interface
                physical_interface.save()


def get_links_via_snmp(snmp_session, device):
    neighbours = snmp_session.get_lldp_neighbours()
    neighbours_list = []
    for neighbour in neighbours:
        if Device.objects.filter(chassis_id=neighbour['remote_chassis_id']).exists():
            interface_id = get_active_or_update_interface_via_snmp(snmp_session, neighbour['local_interface'], device)
            if interface_id:
                remote_device = Device.objects.get(chassis_id=neighbour['remote_chassis_id'])
                if device.id > remote_device.id:
                    neighbours_list.append({
                        'local_interface_id': interface_id,
                        'remote_device_id': remote_device.id,
                        'remote_interface': neighbour['remote_interface'],
                        'is_remote_interface_is_number': neighbour['is_remote_interface_is_number']
                    })
    update_aggregations_via_snmp(snmp_session, device)
    return neighbours_list


def update_device_via_netconf(device):
    try:
        with NetconfSession(device) as netconf_session:
            update_chassis_id(netconf_session, device)
            update_name(netconf_session, device)
            return get_links_via_netconf(netconf_session, device)
    except junos.exception.ConnectAuthError:
        logger.warning(f"Authentication error (host: {device.ip_address}, pk: {device.pk})")
        return []
    except junos.exception.ConnectError:
        logger.warning(f"Connection error (host: {device.ip_address}, pk: {device.pk})")
        device.connection_is_active = False
        device.save()
        return []


def get_active_or_update_interface_via_netconf(netconf_session, interface_name, interface_aggregation_name, device):
    interface = Interface.objects.get_or_none(device=device, name=interface_name, active=True)
    if interface is not None:
        return interface.id
    else:
        interface_details = netconf_session.get_interface(interface_name)
        if interface_details:
            interface, _ = Interface.objects.get_or_create(device=device, number=interface_details['number'])
            interface.speed = interface_details['speed']
            interface.name = interface_details['name']
            interface.active = True
            if interface_aggregation_name:
                aggregate_interface = Interface.objects.get_or_none(device=device, name=interface_aggregation_name,
                                                                    active=True)

                if aggregate_interface is None:
                    aggregate_interface_detail = netconf_session.get_interface(interface_aggregation_name)
                    aggregate_interface, _ = Interface.objects.get_or_create(
                        device=device, number=aggregate_interface_detail['number'])
                    aggregate_interface.active = True
                    aggregate_interface.name = aggregate_interface_detail['name']
                    aggregate_interface.speed = aggregate_interface_detail['speed']
                    aggregate_interface.save()
                interface.aggregate_interface = aggregate_interface
            else:
                interface.aggregate_interface = None
            interface.save()
            return interface.id


def get_links_via_netconf(netconf_session, device):
    neighbours = netconf_session.get_lldp_neighbours()
    neighbours_list = []
    for (local_interface_name, remote_chassis_id) in neighbours:
        if Device.objects.filter(chassis_id=remote_chassis_id).exists():
            lldp_neighbour_details = netconf_session.get_lldp_neighbour_details(local_interface_name)
            for neighbour in lldp_neighbour_details:
                if Device.objects.filter(chassis_id=neighbour['remote_chassis_id']).exists():
                    interface_id = get_active_or_update_interface_via_netconf(netconf_session,
                                                                              neighbour['local_interface'],
                                                                              neighbour['parent_interface'], device)
                    if interface_id:
                        remote_device = Device.objects.get(chassis_id=neighbour['remote_chassis_id'])
                        if device.id > remote_device.id:
                            neighbours_list.append({
                                'local_interface_id': interface_id,
                                'remote_device_id': remote_device.id,
                                'remote_interface': neighbour['remote_interface_number'],
                                'is_remote_interface_is_number': True
                            })
    return neighbours_list


def update_links(neighbours):
    for neighbour in neighbours:
        remote_device = Device.objects.get(pk=neighbour['remote_device_id'])
        try:
            local_interface = Interface.objects.get(pk=neighbour['local_interface_id'])
            if neighbour['is_remote_interface_is_number']:
                remote_interface = get_interface_by_number(remote_device, neighbour['remote_interface'])
            else:
                remote_interface = get_interface_by_name(remote_device, neighbour['remote_interface'])
            link, _ = Link.objects.get_or_create(local_interface=local_interface, remote_interface=remote_interface)
            link.active = True
            link.save()
        except (Interface.DoesNotExist, Interface.MultipleObjectsReturned) as e:
            logger.warning(e)


def get_interface_by_number(device, interface_number):
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
