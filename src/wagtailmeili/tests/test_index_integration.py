# src/wagtailmeili/tests/test_index.py
import pytest
from django.db import models
from requests import Response
from wagtail.search import index as wagtail_index
from wagtail.models import Page
from wagtailmeili.index import MeilisearchIndex, IndexOperationStatus
from wagtailmeili.testapp.models import MoviePage
from meilisearch.errors import MeilisearchApiError

def test_index_initialization(meilisearch_index):
    """Test the initialization of MeilisearchIndex."""
    assert meilisearch_index.name == "wagtailmeili_testapp_moviepage"
    assert meilisearch_index.primary_key == "id"
    assert meilisearch_index.documents == []
    assert meilisearch_index.model == MoviePage


def test_skip_unpublished_pages(meilisearch_backend, load_movies_data):
    """Test that unpublished pages are skipped during indexing."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)
    movie = MoviePage.objects.first()
    movie.live = False

    documents = meili_index.prepare_documents(MoviePage, [movie])
    assert len(documents) == 0


@pytest.mark.django_db
def test_add_items(meilisearch_backend, load_movies_data, clean_meilisearch_index):
    """Test adding multiple items to the index."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)
    meili_index.add_model(MoviePage)

    movies = MoviePage.objects.all()[:2]
    task_info = meili_index.add_items(MoviePage, list(movies))

    assert task_info is not None
    # Wait for indexing to complete
    meilisearch_backend.client.wait_for_task(task_info.task_uid)

    # Verify documents were indexed
    docs = meili_index.index.get_documents()
    assert docs.total >= 2


def test_update_index_settings(meilisearch_backend, clean_meilisearch_index):
    """Test updating index settings."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)
    meili_index.add_model(MoviePage)

    task_info = meili_index.update_index_settings()
    assert task_info is not None

    # Wait for settings update to complete
    meilisearch_backend.client.wait_for_task(task_info.task_uid)

    # Verify settings were updated
    settings = meili_index.index.get_settings()
    assert 'title' in settings['searchableAttributes']
    assert 'rankingRules' in settings
    assert 'typoTolerance' in settings


@pytest.mark.django_db
def test_delete_item(meilisearch_backend, load_movies_data, clean_meilisearch_index):
    """Test deleting an item from the index."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)
    meili_index.add_model(MoviePage)

    movie = MoviePage.objects.first()
    meili_index.add_item(movie)

    # Delete the item
    task_info = meili_index.delete_item(movie.id)
    meilisearch_backend.client.wait_for_task(task_info.task_uid)

    # Verify document was deleted
    docs = meili_index.index.get_documents()
    assert not any(doc['id'] == movie.id for doc in docs.results)


def test_serialize_value(meilisearch_backend):
    """Test serialization of different value types."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)

    # Test string serialization
    assert meili_index.serialize_value("test") == "test"

    # Test list serialization
    assert meili_index.serialize_value(["a", "b"]) == "a, b"

    # Test dict serialization
    assert meili_index.serialize_value({"key": "value"}) == "value"

    # Test empty value
    assert meili_index.serialize_value(None) == ""


def test_validate_model_skipped(meilisearch_backend):
    """Test model validation when model is in skip_models list."""

    class SkippedModel(models.Model, wagtail_index.Indexed):

        search_fields = ["id"]

        class Meta:
            app_label = 'wagtailmeili'

    meilisearch_backend.skip_models = ['wagtailmeili.skippedmodel']
    index = MeilisearchIndex(meilisearch_backend, SkippedModel)

    status = index._validate_model(SkippedModel)
    assert status == IndexOperationStatus.SKIPPED


def test_validate_page_model_skipped(meilisearch_backend):
    """Test model validation when a Page is in skip_models list."""

    class SkippedPage(Page):

        class Meta:
            app_label = 'wagtailmeili'

    meilisearch_backend.skip_models = ['wagtailmeili.skippedpage']
    index = MeilisearchIndex(meilisearch_backend, SkippedPage)

    status = index._validate_model(SkippedPage)
    assert status == IndexOperationStatus.SKIPPED


def test_validate_model_not_indexed(meilisearch_backend):
    """Test model validation when model is not indexed."""

    class UnindexedModel(models.Model):
        pass

    index = MeilisearchIndex(meilisearch_backend, UnindexedModel)
    status = index._validate_model(UnindexedModel)
    assert status == IndexOperationStatus.IS_NOT_INDEXED


def test_add_model_error_handling(meilisearch_backend, monkeypatch):
    """Test error handling when creating an index fails."""

    def mock_create_index(*args, **kwargs):
        response = Response()
        response.status_code = 400
        response._content = b'{"message": "Test error", "code": "index_creation_failed"}'
        raise MeilisearchApiError("Test error message", response)

    monkeypatch.setattr(meilisearch_backend.client, "create_index", mock_create_index)
    index = MeilisearchIndex(meilisearch_backend, MoviePage)

    result = index.add_model(MoviePage)
    assert result is None


@pytest.mark.django_db
def test_serialize_queryset(meilisearch_backend, load_movies_data):
    """Test serialization of QuerySet objects."""
    index = MeilisearchIndex(meilisearch_backend, MoviePage)
    queryset = MoviePage.objects.all()

    serialized = index.serialize_value(queryset)
    assert isinstance(serialized, str)
    assert len(serialized) > 0


@pytest.mark.django_db
def test_serialize_manager(meilisearch_backend, load_movies_data):
    """Test serialization of Manager objects."""
    index = MeilisearchIndex(meilisearch_backend, MoviePage)
    manager = MoviePage.objects

    serialized = index.serialize_value(manager)
    assert isinstance(serialized, list)
    assert len(serialized) > 0


@pytest.mark.django_db
def test_skip_by_field_value(meilisearch_backend, load_movies_data, clean_meilisearch_index):
    """Test skipping documents based on field values.

    Another version of this test is in test_backend_integration
    test_skip_models(meilisearch_backend) relying on the settings.

    """
    movie = MoviePage.objects.first()
    meilisearch_backend.skip_models_by_field_value = {
        'wagtailmeili_testapp.moviepage': {
            'field': 'title',
            'value': movie.title
        }
    }

    for movie in MoviePage.objects.all():
        meilisearch_backend.add(movie)

    tasks = meilisearch_backend.client.get_tasks()
    if tasks.results:
        last_task = tasks.results[0]
        meilisearch_backend.client.wait_for_task(last_task.uid)

    total_movies = MoviePage.objects.count()

    index = MeilisearchIndex(meilisearch_backend, MoviePage)
    documents = index.index.get_documents()

    assert documents.total == total_movies - 1
    doc_titles = [doc.title for doc in documents.results]
    assert movie.title not in doc_titles


def test_custom_ranking_rules(meilisearch_backend, clean_meilisearch_index, original_ranking_rules):
    """Test applying custom ranking rules to index."""
    class CustomMoviePage(MoviePage):
        ranking_rules = ['date:asc', 'custom_rule']

    index = MeilisearchIndex(meilisearch_backend, CustomMoviePage)
    index.add_model(CustomMoviePage)

    tasks = meilisearch_backend.client.get_tasks()
    if tasks.results:
        last_task = tasks.results[0]
        meilisearch_backend.client.wait_for_task(last_task.uid)

    settings = meilisearch_backend.ranking_rules.copy()
    expected_rules = original_ranking_rules + ['date:asc', 'custom_rule']
    assert settings == expected_rules


def test_error_handling_settings_update(meilisearch_backend, monkeypatch):
    """Test error handling during settings update."""

    def mock_update_settings(*args, **kwargs):
        raise MeilisearchApiError("Settings update error")

    index = MeilisearchIndex(meilisearch_backend, MoviePage)
    monkeypatch.setattr(index.index, "update_settings", mock_update_settings)

    task_info = index.update_index_settings()
    assert task_info is None


@pytest.mark.django_db
def test_related_fields_processing(meilisearch_backend, clean_meilisearch_index):
    """Test processing of different types of related fields."""
    from wagtailmeili.testapp.models import Author, RelatedMoviePage
    from wagtail.models import Page

    # Create test data
    author = Author.objects.create(name="Test Author")

    # Get the movies index page
    movies_index = Page.objects.get(slug='movies')

    # Create related movie pages
    movie1 = RelatedMoviePage(
            title="Related Movie 1",
            author=author,
    )
    movies_index.add_child(instance=movie1)

    movie2 = RelatedMoviePage(
            title="Related Movie 2",
            author=author,
    )
    movies_index.add_child(instance=movie2)

    # Add related movies
    movie1.related_movies.add(movie2)

    # Initialize index and process the page
    index = MeilisearchIndex(meilisearch_backend, RelatedMoviePage)
    documents = index.prepare_documents(RelatedMoviePage, movie1)

    # Verify the processed document
    assert len(documents) == 1
    document = documents[0]

    # Check ForeignKey (author) processing
    assert 'author' in document
    assert document['author']['name'] == "Test Author"

    # Check ManyToMany (related_movies) processing
    assert 'related_movies' in document
    assert len(document['related_movies']) == 1
    assert document['related_movies'][0]['title'] == "Related Movie 2"

    # Verify the document for movie2
    documents_reverse = index.prepare_documents(RelatedMoviePage, movie2)
    assert len(documents_reverse) == 1
    document_reverse = documents_reverse[0]
    assert document_reverse['title'] == "Related Movie 2"
    assert document_reverse['author']['name'] == "Test Author"


@pytest.mark.django_db
def test_sortable_attributes(meilisearch_backend, clean_meilisearch_index):
    """Test applying sortable attributes to index."""

    class SortableMoviePage(MoviePage):
        sortable_attributes = ['title', 'release_date']

    index = MeilisearchIndex(meilisearch_backend, SortableMoviePage)
    index.add_model(SortableMoviePage)

    # Wait for any pending tasks
    tasks = meilisearch_backend.client.get_tasks()
    if tasks.results:
        last_task = tasks.results[0]
        meilisearch_backend.client.wait_for_task(last_task.uid)

    # Get the index settings
    settings = index.index.get_settings()

    # Verify sortable attributes are present in the settings
    assert 'sortableAttributes' in settings
    assert set(settings['sortableAttributes']) == set(['title', 'release_date'])


@pytest.mark.django_db
def test_no_sortable_attributes(meilisearch_backend, clean_meilisearch_index):
    """Test index settings when no sortable attributes are defined."""

    class RegularMoviePage(MoviePage):
        pass  # No sortable_attributes defined

    index = MeilisearchIndex(meilisearch_backend, RegularMoviePage)
    index.add_model(RegularMoviePage)

    # Wait for any pending tasks
    tasks = meilisearch_backend.client.get_tasks()
    if tasks.results:
        last_task = tasks.results[0]
        meilisearch_backend.client.wait_for_task(last_task.uid)

    # Get the index settings
    settings = index.index.get_settings()

    # Verify sortable attributes is empty when not defined
    assert 'sortableAttributes' in settings
    assert settings['sortableAttributes'] == []