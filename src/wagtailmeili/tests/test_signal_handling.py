import pytest
from unittest.mock import patch, MagicMock
from wagtail.signals import page_unpublished

from wagtailmeili.testapp.models import MoviePage


@pytest.fixture
def test_movie(movies_index_page):
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
def test_page_unpublished_signal_removes_from_index(mock_get_backend, test_movie):
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
        movie_pk = test_movie.pk
        test_movie.live = False
        test_movie.save()

        page_unpublished.send(sender=MoviePage, instance=test_movie)

        mock_get_backend.assert_called_with('meilisearch')
        mock_backend.get_index_for_model.assert_called_with(MoviePage)
        mock_index.delete_item.assert_called_with(movie_pk)

    finally:
        page_unpublished.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
@patch('wagtailmeili.signals.get_search_backend')
def test_page_unpublished_signal_handles_backend_error(mock_get_backend, test_movie):
    mock_backend = MagicMock()
    mock_index = MagicMock()
    mock_index.delete_item.side_effect = Exception("Backend error")
    mock_backend.get_index_for_model.return_value = mock_index
    mock_get_backend.return_value = mock_backend

    from wagtailmeili.signals import handle_page_unpublish

    def test_handler(sender, instance, **kwargs):
        if sender == MoviePage:
            handle_page_unpublish(sender, instance, **kwargs)

    page_unpublished.connect(test_handler, sender=MoviePage)

    try:
        test_movie.live = False
        test_movie.save()

        page_unpublished.send(sender=MoviePage, instance=test_movie)

        mock_get_backend.assert_called_with('meilisearch')

    finally:
        page_unpublished.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
@patch('wagtailmeili.signals.get_search_backend')
def test_page_unpublished_signal_skips_non_indexed_models(mock_get_backend, test_movie):
    mock_backend = MagicMock()
    mock_backend.get_index_for_model.return_value = None
    mock_get_backend.return_value = mock_backend

    from wagtailmeili.signals import handle_page_unpublish

    def test_handler(sender, instance, **kwargs):
        if sender == MoviePage:
            handle_page_unpublish(sender, instance, **kwargs)

    page_unpublished.connect(test_handler, sender=MoviePage)

    try:
        test_movie.live = False
        test_movie.save()

        page_unpublished.send(sender=MoviePage, instance=test_movie)

        mock_get_backend.assert_called_with('meilisearch')
        mock_backend.get_index_for_model.assert_called_with(MoviePage)

    finally:
        page_unpublished.disconnect(test_handler, sender=MoviePage)


@pytest.mark.django_db
def test_signal_handlers_are_automatically_connected():
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