"""Tests for index cleanup functionality."""
import pytest
from unittest.mock import MagicMock
from meilisearch.errors import MeilisearchApiError
from meilisearch import Client

from wagtailmeili.index import MeilisearchIndex
from wagtailmeili.backend import MeilisearchBackend
from wagtailmeili.testapp.models import MoviePage


@pytest.fixture
def test_movies(movies_index_page):
    """Create test movies for cleanup tests."""
    movie1 = MoviePage(
        title="Test Movie 1",
        slug="test-movie-1",
        overview="A test movie",
        genres=["Drama"],
        live=True,
    )
    movies_index_page.add_child(instance=movie1)
    
    movie2 = MoviePage(
        title="Test Movie 2",
        slug="test-movie-2",
        overview="Another test movie",
        genres=["Comedy"],
        live=True,
    )
    movies_index_page.add_child(instance=movie2)
    
    return movie1, movie2


@pytest.mark.django_db
def test_delete_item_removes_from_index(test_movies):
    """Test that delete_item removes a document from the index."""
    movie1, movie2 = test_movies
    
    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    
    index = MeilisearchIndex(backend, MoviePage)
    mock_task = MagicMock()
    mock_task.task_uid = "test-task-123"
    index.index.delete_document = MagicMock(return_value=mock_task)
    
    result = index.delete_item(movie1.pk)
    index.index.delete_document.assert_called_once_with(movie1.pk)
    assert result == mock_task


@pytest.mark.django_db
def test_delete_item_handles_nonexistent_document(test_movies):
    """Test that delete_item handles deletion of non-existent documents gracefully."""
    movie1, movie2 = test_movies

    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    
    index = MeilisearchIndex(backend, MoviePage)

    error_response = MagicMock()
    error_response.text = '{"message": "document_not_found", "code": "document_not_found"}'
    error_response.status_code = 404
    error = MeilisearchApiError("document_not_found", error_response)
    index.index.delete_document = MagicMock(side_effect=error)

    result = index.delete_item(999)
    assert result is None


@pytest.mark.django_db
def test_delete_item_handles_model_instance(test_movies):
    """Test that delete_item can handle both model instances and primary keys."""
    movie1, movie2 = test_movies
    
    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    
    index = MeilisearchIndex(backend, MoviePage)
    mock_task = MagicMock()
    index.index.delete_document = MagicMock(return_value=mock_task)
    result = index.delete_item(movie1)

    index.index.delete_document.assert_called_once_with(movie1.pk)
    assert result == mock_task


@pytest.mark.django_db
def test_bulk_delete_items_removes_multiple_documents(test_movies):
    """Test that bulk_delete_items removes multiple documents."""
    movie1, movie2 = test_movies

    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    
    index = MeilisearchIndex(backend, MoviePage)
    
    mock_task = MagicMock()
    index.index.delete_documents = MagicMock(return_value=mock_task)

    pks = [movie1.pk, movie2.pk]
    result = index.bulk_delete_items(pks)
    
    index.index.delete_documents.assert_called_once_with(pks)
    assert result == mock_task


@pytest.mark.django_db
def test_bulk_delete_items_handles_empty_list():
    """Test that bulk_delete_items handles empty list gracefully."""
    # Mock backend and index
    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    
    index = MeilisearchIndex(backend, MoviePage)

    result = index.bulk_delete_items([])
    assert result is None


@pytest.mark.django_db
def test_cleanup_stale_documents_removes_orphaned_docs(test_movies):
    """Test that cleanup_stale_documents removes documents not in live_pks."""
    movie1, movie2 = test_movies
    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    index = MeilisearchIndex(backend, MoviePage)
    mock_docs = MagicMock()
    mock_docs.results = [
        {"id": str(movie1.pk)},
        {"id": str(movie2.pk)},
        {"id": "999"},  # This is stale
        {"id": "888"},  # This is also stale
    ]
    index.index.get_documents = MagicMock(return_value=mock_docs)
    index.bulk_delete_items = MagicMock()
    live_pks = [movie1.pk]
    index.cleanup_stale_documents(live_pks)
    
    expected_stale_ids = [str(movie2.pk), "999", "888"]
    index.bulk_delete_items.assert_called_once()
    actual_stale_ids = index.bulk_delete_items.call_args[0][0]
    assert set(actual_stale_ids) == set(expected_stale_ids)


@pytest.mark.django_db
def test_cleanup_stale_documents_handles_no_stale_docs(test_movies):
    """Test that cleanup_stale_documents handles case with no stale documents."""
    movie1, movie2 = test_movies
    
    # Mock backend and index
    backend = MagicMock(spec=MeilisearchBackend)
    backend.client = MagicMock(spec=Client)
    backend.skip_models = []
    backend.skip_models_by_field_value = {}
    index = MeilisearchIndex(backend, MoviePage)
    mock_docs = MagicMock()
    mock_docs.results = [
        {"id": str(movie1.pk)},
        {"id": str(movie2.pk)},
    ]
    index.index.get_documents = MagicMock(return_value=mock_docs)
    
    index.bulk_delete_items = MagicMock()
    live_pks = [movie1.pk, movie2.pk]
    index.cleanup_stale_documents(live_pks)
    
    index.bulk_delete_items.assert_not_called()
