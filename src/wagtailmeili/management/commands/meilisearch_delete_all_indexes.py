from django.core.management.base import BaseCommand
from wagtail.search.backends import get_search_backend


class Command(BaseCommand):
    """Delete all Meilisearch indexes"""

    help = 'Delete all Meilisearch indexes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        if not options['force']:
            confirm = input("This will delete all Meilisearch indexes. Are you sure? [y/N] ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled.")
                return

        backend = get_search_backend()
        backend.delete_all_indexes()
        self.stdout.write(self.style.SUCCESS("Successfully deleted all indexes"))