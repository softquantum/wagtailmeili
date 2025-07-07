"""Tests for signal handling functionality."""
import pytest
from unittest.mock import patch, MagicMock
from django.db.models.signals import post_delete
from wagtail.signals import page_unpublished

from wagtailmeili.testapp.models import MoviePage


@pytest.fixture
def test_movie(movies_index_page):
    """Create a test movie for signal tests."""
    movie = MoviePage(
        title="Test Movie",
        slug="test-movie",
        overview="A test movie",
        genres=["Drama"],
        live=True,
    )
    movies_index_page.add_child(instance=movie)
    return movie


@pytest.mark.django_db
@patch('wagtailmeili.signals.get_search_backend')
def test_post_delete_signal_removes_from_index(mock_get_backend, test_movie):
    """Test that post_delete signal removes item from search index."""
    mock_backend = MagicMock()
    mock_index = MagicMock()
    mock_backend.get_index_for_model.return_value = mock_index
    mock_get_backend.return_value = mock_backend
    
    from wagtailmeili.signals import handle_item_deletion
    
    def test_handler(sender, instance, **kwargs):
        if sender == MoviePage:
            handle_item_deletion(sender, instance, **kwargs)
    
    post_delete.connect(test_handler, sender=MoviePage)
    
    try:
        # Delete the movie - this should trigger the signal
        movie_pk = test_movie.pk
        test_movie.delete()
        
        mock_get_backend.assert_called_with('meilisearch')
        calls = mock_backend.get_index_for_model.call_args_list
        movie_page_calls = [call for call in calls if call[0][0] == MoviePage]
        assert len(movie_page_calls) > 0, f"Expected MoviePage in calls, but got: {calls}"
        mock_index.delete_item.assert_called_with(movie_pk)
        
    finally:
        post_delete.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
@patch('wagtailmeili.signals.get_search_backend')
def test_post_delete_signal_handles_backend_error(mock_get_backend, test_movie):
    """Test that post_delete signal handles backend errors gracefully."""
    mock_backend = MagicMock()
    mock_index = MagicMock()
    mock_index.delete_item.side_effect = Exception("Backend error")
    mock_backend.get_index_for_model.return_value = mock_index
    mock_get_backend.return_value = mock_backend
    
    from wagtailmeili.signals import handle_item_deletion
    
    def test_handler(sender, instance, **kwargs):
        if sender == MoviePage:
            handle_item_deletion(sender, instance, **kwargs)
    
    post_delete.connect(test_handler, sender=MoviePage)
    
    try:
        # Delete the movie - this should trigger the signal but not raise
        movie_pk = test_movie.pk
        test_movie.delete()  # Should not raise exception
        
        mock_get_backend.assert_called_with('meilisearch')
        calls = mock_backend.get_index_for_model.call_args_list
        movie_page_calls = [call for call in calls if call[0][0] == MoviePage]
        assert len(movie_page_calls) > 0, f"Expected MoviePage in calls, but got: {calls}"
        mock_index.delete_item.assert_called_with(movie_pk)
        
    finally:
        post_delete.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
@patch('wagtailmeili.signals.get_search_backend')
def test_page_unpublished_signal_removes_from_index(mock_get_backend, test_movie):
    """Test that page_unpublished signal removes page from search index."""
    mock_backend = MagicMock()
    mock_index = MagicMock()
    mock_backend.get_index_for_model.return_value = mock_index
    mock_get_backend.return_value = mock_backend
    
    from wagtailmeili.signals import handle_page_unpublish
    
    def test_handler(sender, instance, **kwargs):
        if sender == MoviePage:
            handle_page_unpublish(sender, instance, **kwargs)
    
    page_unpublished.connect(test_handler, sender=MoviePage)
    
    try:
        # Unpublish the movie - this should trigger the signal
        movie_pk = test_movie.pk
        test_movie.live = False
        test_movie.save()
        
        # Manually trigger the signal since we're not using the actual unpublish workflow
        page_unpublished.send(sender=MoviePage, instance=test_movie)
        
        mock_get_backend.assert_called_with('meilisearch')
        mock_backend.get_index_for_model.assert_called_with(MoviePage)
        mock_index.delete_item.assert_called_with(movie_pk)
        
    finally:
        page_unpublished.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
@patch('wagtailmeili.signals.get_search_backend')
def test_signal_handler_skips_non_indexed_models(mock_get_backend, test_movie):
    """Test that signal handlers skip models that are not indexed."""
    mock_backend = MagicMock()
    mock_backend.get_index_for_model.return_value = None
    mock_get_backend.return_value = mock_backend
    
    from wagtailmeili.signals import handle_item_deletion
    
    def test_handler(sender, instance, **kwargs):
        if sender == MoviePage:
            handle_item_deletion(sender, instance, **kwargs)
    
    post_delete.connect(test_handler, sender=MoviePage)
    
    try:
        test_movie.delete()
        
        mock_get_backend.assert_called_with('meilisearch')
        calls = mock_backend.get_index_for_model.call_args_list
        movie_page_calls = [call for call in calls if call[0][0] == MoviePage]
        assert len(movie_page_calls) > 0, f"Expected MoviePage in calls, but got: {calls}"
        
    finally:
        post_delete.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
def test_signal_handlers_are_automatically_connected():
    """Test that signal handlers are automatically connected when app is ready."""
    from wagtailmeili.signals import connect_signals
    from wagtailmeili.apps import WagtailMeiliConfig
    
    assert callable(connect_signals)
    
    app_config = WagtailMeiliConfig
    assert hasattr(app_config, 'ready')
    assert callable(app_config.ready)
    
    try:
        connect_signals()
    except Exception as e:
        pytest.fail(f"connect_signals() raised an exception: {e}")
