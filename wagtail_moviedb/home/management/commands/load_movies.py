import json
import os
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management.base import BaseCommand
from wagtail.models import Page
from home.models import MoviePage

ASSET_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


class Command(BaseCommand):
    """Load movie data from a JSON file into the MoviePage model."""

    help = (
        "Load movie data from a JSON file and create MoviePage entries in the Wagtail page tree. "
        "The command will create movie pages as children of the specified parent page."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-file',
            type=str,
            help=(
                'Path to the JSON file containing movie data, relative to the assets directory. '
                'Defaults to "movies_500.json"'
            )
        )
        parser.add_argument(
            '--parent-page-id',
            type=int,
            help='ID of the parent page under which movie pages will be created. Defaults to 3 (home page)'
        )

    def handle(self, *args, **options):
        json_file = options.get("json_file") or "movies_selection.json"
        json_file_path = ASSET_DIR / json_file

        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found at {json_file_path}")

        parent_page_id = options.get("parent_page_id") or 3

        with open(json_file_path, "r") as file:
            data = json.load(file)

        parent_page = Page.objects.get(id=parent_page_id)

        for entry in data:
            release_date = datetime.fromtimestamp(entry['release_date'], tz=timezone.utc).date()
            movie_page = MoviePage(
                title=entry['title'],
                overview=entry['overview'],
                genres=entry['genres'],
                poster=entry['poster'],
                release_date=release_date,
            )
            parent_page.add_child(instance=movie_page)
            movie_page.save_revision().publish()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created movie pages from {json_file}"
            )
        )
