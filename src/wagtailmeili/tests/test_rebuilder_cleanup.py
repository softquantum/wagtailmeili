"""Tests for rebuilder cleanup functionality."""
import pytest
from unittest.mock import patch, MagicMock

from wagtailmeili.rebuilder import MeilisearchRebuilder
from wagtailmeili.testapp.models import MoviePage


@pytest.fixture
def test_movies_for_rebuild(movies_index_page):
    """Create test movies for rebuilder tests."""
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
    
    # Create unpublished movie
    unpublished_movie = MoviePage(
        title="Unpublished Movie",
        slug="unpublished-movie",
        overview="This should not be indexed",
        genres=["Horror"],
        live=False,
    )
    movies_index_page.add_child(instance=unpublished_movie)
    
    return movie1, movie2, unpublished_movie


@pytest.mark.django_db
def test_rebuilder_cleans_stale_documents_during_rebuild(test_movies_for_rebuild):
    """Test that rebuilder removes stale documents during rebuild."""
    movie1, movie2, unpublished_movie = test_movies_for_rebuild
    
    mock_index = MagicMock()
    mock_backend = MagicMock()
    mock_backend.get_index_for_model.return_value = mock_index
    
    rebuilder = MeilisearchRebuilder(mock_index)
    rebuilder.backend = mock_backend
    
    rebuilder._get_index_document_ids = MagicMock(return_value={
        str(movie1.pk), str(movie2.pk), "999", "888"  # 999 and 888 are stale
    })
    rebuilder._bulk_delete_documents = MagicMock()
    
    rebuilder.rebuild_index_for_model(MoviePage)
    
    rebuilder._get_index_document_ids.assert_called_once_with(mock_index)
    
    rebuilder._bulk_delete_documents.assert_called_once()
    call_args = rebuilder._bulk_delete_documents.call_args
    stale_ids = call_args[0][1]  # Second argument is the set of stale IDs
    assert "999" in stale_ids
    assert "888" in stale_ids


@pytest.mark.django_db
def test_get_index_document_ids_returns_current_document_ids():
    """Test that _get_index_document_ids returns current document IDs from index."""
    mock_index = MagicMock()
    mock_documents = MagicMock()
    mock_documents.results = [
        {"id": "1"}, {"id": "2"}, {"id": "3"}
    ]
    mock_index.index.get_documents.return_value = mock_documents
    
    rebuilder = MeilisearchRebuilder(mock_index)
    
    result = rebuilder._get_index_document_ids(mock_index)
    
    expected_ids = {"1", "2", "3"}
    assert result == expected_ids
    
    mock_index.index.get_documents.assert_called_once_with(fields=['id'])


@pytest.mark.django_db
def test_get_index_document_ids_handles_api_error():
    """Test that _get_index_document_ids handles API errors gracefully."""
    mock_index = MagicMock()
    mock_index.index.get_documents.side_effect = Exception("API Error")
    
    rebuilder = MeilisearchRebuilder(mock_index)
    
    result = rebuilder._get_index_document_ids(mock_index)
    
    assert result == set()


@pytest.mark.django_db
def test_bulk_delete_documents_deletes_multiple_documents():
    """Test that _bulk_delete_documents deletes multiple documents."""
    mock_index = MagicMock()
    mock_task = MagicMock()
    mock_task.task_uid = "test-task-123"
    mock_index.index.delete_documents.return_value = mock_task
    
    rebuilder = MeilisearchRebuilder(mock_index)
    
    rebuilder._wait_for_task_completion = MagicMock()
    
    document_ids = {"1", "2", "3"}
    rebuilder._bulk_delete_documents(mock_index, document_ids)
    
    mock_index.index.delete_documents.assert_called_once()
    call_args = mock_index.index.delete_documents.call_args
    actual_ids = set(call_args[0][0])
    expected_ids = {"1", "2", "3"}
    assert actual_ids == expected_ids
    
    rebuilder._wait_for_task_completion.assert_called_once_with(mock_task)


@pytest.mark.django_db
def test_bulk_delete_documents_handles_api_error():
    """Test that _bulk_delete_documents handles API errors gracefully."""
    mock_index = MagicMock()
    mock_index.index.delete_documents.side_effect = Exception("API Error")
    
    rebuilder = MeilisearchRebuilder(mock_index)
    
    document_ids = {"1", "2", "3"}
    rebuilder._bulk_delete_documents(mock_index, document_ids)
    
    mock_index.index.delete_documents.assert_called_once()
    call_args = mock_index.index.delete_documents.call_args
    actual_ids = set(call_args[0][0])
    expected_ids = {"1", "2", "3"}
    assert actual_ids == expected_ids


@pytest.mark.django_db
def test_rebuilder_only_considers_live_pages_for_cleanup(test_movies_for_rebuild):
    """Test that rebuilder only considers live pages when determining stale documents."""
    movie1, movie2, unpublished_movie = test_movies_for_rebuild
    
    mock_index = MagicMock()
    rebuilder = MeilisearchRebuilder(mock_index)
    rebuilder.backend = MagicMock()
    rebuilder.backend.get_index_for_model.return_value = mock_index
    
    rebuilder._get_index_document_ids = MagicMock(return_value={
        str(movie1.pk), str(movie2.pk), str(unpublished_movie.pk)
    })
    rebuilder._bulk_delete_documents = MagicMock()
    
    with patch.object(MoviePage.objects, 'filter') as mock_filter:
        mock_values_list = MagicMock()
        mock_values_list.return_value = [movie1.pk, movie2.pk]  # Only live movies
        mock_filter.return_value.values_list = mock_values_list
        
        rebuilder.rebuild_index_for_model(MoviePage)
        
        mock_filter.assert_called_once_with(live=True)
        
        rebuilder._bulk_delete_documents.assert_called_once()
        call_args = rebuilder._bulk_delete_documents.call_args
        stale_ids = call_args[0][1]  # Second argument is the set of stale IDs
        assert str(unpublished_movie.pk) in stale_ids


@pytest.mark.django_db
def test_rebuilder_handles_models_without_live_field():
    """Test that rebuilder handles models without 'live' field appropriately."""
    class SimpleModel:
        objects = MagicMock()
        objects.all.return_value.values_list.return_value = [1, 2, 3]
    
    mock_index = MagicMock()
    rebuilder = MeilisearchRebuilder(mock_index)
    
    rebuilder._get_index_document_ids = MagicMock(return_value={"1", "2", "3", "4"})
    rebuilder._bulk_delete_documents = MagicMock()
    rebuilder.backend = MagicMock()
    rebuilder.backend.get_index_for_model.return_value = mock_index
    
    rebuilder.rebuild_index_for_model(SimpleModel)
    
    SimpleModel.objects.all.assert_called_once()
    
    rebuilder._bulk_delete_documents.assert_called_once()
    call_args = rebuilder._bulk_delete_documents.call_args
    stale_ids = call_args[0][1]  # Second argument is the set of stale IDs
    assert "4" in stale_ids
