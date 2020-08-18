from django.core.management.base import BaseCommand
from data.tasks import check_links


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        check_links()
