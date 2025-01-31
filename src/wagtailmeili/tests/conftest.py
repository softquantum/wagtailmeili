import json
import logging
import pytest

from pathlib import Path
from wagtail.models import Page, Locale
from django.db import models

from wagtailmeili.rebuilder import MeilisearchRebuilder
from wagtailmeili.testapp import settings as test_settings
from wagtailmeili.testapp.models import MoviePage, MoviePageIndex
from wagtailmeili.utils import is_in_meilisearch

logger = logging.getLogger(__name__)

from wagtailmeili.backend import MeilisearchBackend

# Update the fixture path
MOVIES_FILE = Path(__file__).parent.parent / "testapp" / "fixtures" / "movies_selection.json"


def pytest_configure(config):
    """Verify that wagtail is in the PYTHONPATH and log the version for debugging purposes."""
    import sys
    print("Python path:", sys.path)
    try:
        import wagtail
        print("Wagtail found at:", wagtail.__file__)
        from wagtail import VERSION
        print("Wagtail version:", VERSION)
        print("Database engine:", test_settings.DATABASES['default']['ENGINE'])
        print("Database name:", test_settings.DATABASES['default']['NAME'])

    except ImportError as e:
        print("Failed to import:", e)
        print("Current sys.modules keys:", [k for k in sys.modules.keys() if 'wagtail' in k])


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for all tests."""
    logging.basicConfig(level=logging.INFO)


@pytest.fixture
def meilisearch_params():
    """Provide default parameters for initializing MeilisearchBackend."""
    return {
        "HOST": "http://localhost",
        "PORT": "7700",
        "MASTER_KEY": "test_key"
    }


@pytest.fixture
def meilisearch_backend():
    """Real Meilisearch backend for integration tests"""
    return MeilisearchBackend(params=test_settings.WAGTAILSEARCH_BACKENDS["default"])


@pytest.fixture
def meilisearch_rebuilder(meilisearch_backend):
    """Create a rebuilder with the real backend"""
    index = meilisearch_backend.get_index_for_model(MoviePage)
    return MeilisearchRebuilder(index)


@pytest.fixture
def meilisearch_index(meilisearch_backend, clean_meilisearch_index):
    """Create a MeilisearchIndex instance for testing."""
    from wagtailmeili.testapp.models import MoviePage
    index = meilisearch_backend.get_index_for_model(MoviePage)

    # Create the index in Meilisearch
    task = index.client.create_index(index.name)
    index.client.wait_for_task(task.task_uid)

    yield index

    # Cleanup
    if is_in_meilisearch(index.client, index.name):
        index.client.delete_index(index.name)


@pytest.fixture
def test_movies():
    """Create two test movies."""
    from unittest.mock import Mock

    # Create mock MoviePage instances with just the attributes we need
    movie1 = Mock(spec=MoviePage)
    movie1.pk = 1
    movie1.title = "Gone with the wind"
    movie1.slug = "gone-with-the-wind"
    movie1.live = True

    movie2 = Mock(spec=MoviePage)
    movie2.pk = 2
    movie2.title = "John Doe"
    movie2.slug = "john-doe"
    movie2.live = True

    # Mock the get_search_fields method on MoviePage
    MoviePage.get_search_fields = Mock(return_value=[
        Mock(
            field_name='title',
            **{'__class__.__name__': 'SearchField'}  # This makes isinstance(field, SearchField) work
        )
    ])

    return [movie1, movie2]


@pytest.fixture
def load_movies_data(db):
    """Load the movies data into the database."""
    default_locale = Locale.objects.get_or_create(language_code='en')[0]
    print(f"Default locale: {default_locale}")

    movies_index_page = MoviePageIndex.objects.get(slug='movies')
    print(f"Movies index page: {movies_index_page}")

    # Read the JSON file
    try:
        with open(MOVIES_FILE) as f:
            movies_data = json.load(f)
    except FileNotFoundError:
        raise Exception(f"Movies data file not found: {MOVIES_FILE}")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON in movies data file: {MOVIES_FILE}")

    # Create movie pages
    created_movies = []
    for movie_data in movies_data:
        try:
            movie_page = MoviePage(
                title=movie_data['title'],
                slug=movie_data['slug'],
                overview=movie_data['overview'],
                genres=movie_data['genres'],
                poster=movie_data['poster'],
                release_date=movie_data['release_date'],
                locale=default_locale
            )
            movies_index_page.add_child(instance=movie_page)
            created_movies.append(movie_page)
            print(f"Created movie page: {movie_page}")
        except Exception as e:
            raise Exception(f"Failed to create movie {movie_data.get('title', 'unknown')}: {str(e)}")

    return MoviePage.objects.all()


@pytest.fixture
def clean_meilisearch_index(meilisearch_backend):
    """Fixture to clean up Meilisearch index before and after tests."""
    meilisearch_backend.delete_all_indexes()
    yield
    meilisearch_backend.delete_all_indexes()


@pytest.fixture
def original_ranking_rules(meilisearch_backend):
    """Fixture to manage ranking rules state."""
    original_rules = meilisearch_backend.ranking_rules.copy()
    yield original_rules
    meilisearch_backend.ranking_rules = original_rules
