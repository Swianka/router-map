from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission


class Command(BaseCommand):
    help = 'Add user groups if not existing and set permissions'

    def handle(self, *args, **kwargs):
        visualisation_admin_group, _ = Group.objects.get_or_create(name="visualisation_admin")
        visualisation_admin_permissions = Permission.objects.filter(
            codename__in=['change_map', 'add_map', 'change_diagram', 'add_diagram', 'delete_link',
                          'add_device', 'change_device', 'delete_device'])
        visualisation_admin_group.permissions.set(visualisation_admin_permissions)

        account_admin_group, _ = Group.objects.get_or_create(name="account_admin")
        account_admin_permissions = Permission.objects.filter(codename__in=['add_user', 'change_user', 'view_user'])
        account_admin_group.permissions.set(account_admin_permissions)
