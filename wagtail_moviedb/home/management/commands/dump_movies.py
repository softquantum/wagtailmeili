# Create this file at src/wagtailmeili/testapp/management/commands/dump_movies.py

from django.core.management.base import BaseCommand
from home.models import MoviePage
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Dumps MoviePage objects to a JSON file.  The file is not a fixture format.'

    def add_arguments(self, parser):
        parser.add_argument('output', type=str, help='Output JSON file path')

    def handle(self, *args, **options):
        movies = MoviePage.objects.all()
        data = []

        for movie in movies:
            movie_data = {
                'title': movie.title,
                'overview': movie.overview,
                'genres': movie.genres,
                'poster': movie.poster,
                'release_date': movie.release_date.isoformat() if movie.release_date else None,
                'slug': movie.slug,
            }
            data.append(movie_data)

        with open(options['output'], 'w') as f:
            json.dump(data, f, indent=4)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully dumped {len(data)} movies to {options["output"]}')
        )