import pytest
from unittest.mock import patch
from wagtail.search import index as wagtail_search_index
import wagtail

from wagtailmeili.testapp.models import MoviePage

WAGTAIL_VERSION = tuple(wagtail.VERSION[:2])


@pytest.mark.django_db
def test_wagtail_insert_or_update_object_with_unpublished_page(movies_index_page):
    movie = MoviePage(
        title="Test Movie",
        slug="test-movie",
        overview="A test movie",
        genres=["Drama"],
        live=True,
    )
    movies_index_page.add_child(instance=movie)
    movie.save()

    indexed_instance = wagtail_search_index.get_indexed_instance(movie)
    assert indexed_instance is not None, "Published page should return an indexed instance"

    movie.live = False
    movie.save()

    indexed_instance_after_unpublish = wagtail_search_index.get_indexed_instance(movie)

    assert indexed_instance_after_unpublish is not None, (
        "get_indexed_instance() does NOT filter by live status - "
        "it returns the instance regardless of live=False. "
        "This means backends must handle unpublished page cleanup via the page_unpublished signal"
    )


@pytest.mark.django_db
def test_wagtail_get_indexed_objects_includes_unpublished_pages(movies_index_page):
    movie1 = MoviePage(
        title="Published Movie",
        slug="published-movie",
        overview="A published movie",
        genres=["Drama"],
        live=True,
    )
    movies_index_page.add_child(instance=movie1)

    movie2 = MoviePage(
        title="Unpublished Movie",
        slug="unpublished-movie",
        overview="An unpublished movie",
        genres=["Drama"],
        live=False,
    )
    movies_index_page.add_child(instance=movie2)

    indexed_pks = set(MoviePage.get_indexed_objects().values_list('pk', flat=True))

    assert indexed_pks == {movie1.pk, movie2.pk}, (
        "Wagtail does NOT filter by live status in get_indexed_objects(), "
        "so the backend must filter unpublished pages itself"
    )


@pytest.mark.django_db
def test_wagtail_signal_calls_backend_add_method(movies_index_page):
    if WAGTAIL_VERSION >= (6, 4):
        patch_path = 'wagtail.search.tasks.index.insert_or_update_object'
    else:
        patch_path = 'wagtail.search.index.insert_or_update_object'

    with patch(patch_path) as mock_insert_or_update:
        movie = MoviePage(
            title="Test Movie",
            slug="test-movie",
            overview="A test movie",
            genres=["Drama"],
            live=True,
        )
        movies_index_page.add_child(instance=movie)
        movie.save()

        assert mock_insert_or_update.called, f"Wagtail {WAGTAIL_VERSION} insert_or_update_object should be called on save"


@pytest.mark.django_db
def test_meilisearch_index_prepare_documents_filters_unpublished(meilisearch_index, movies_index_page):
    movie = MoviePage(
        title="Test Movie",
        slug="test-movie",
        overview="A test movie",
        genres=["Drama"],
        live=False,
    )
    movies_index_page.add_child(instance=movie)

    documents = meilisearch_index.prepare_documents(MoviePage, [movie])

    assert len(documents) == 0, (
        "MeilisearchIndex.prepare_documents should return empty list for unpublished pages."
    )


@pytest.mark.django_db
def test_page_unpublish_workflow(movies_index_page, meilisearch_backend):
    movie = MoviePage(
        title="Test Movie",
        slug="test-movie-unpublish",
        overview="A test movie",
        genres=["Drama"],
        live=True,
    )
    movies_index_page.add_child(instance=movie)

    index = meilisearch_backend.get_index_for_model(MoviePage)

    documents_published = index.prepare_documents(MoviePage, [movie])
    assert len(documents_published) == 1, "Should create document for published page"

    movie.live = False
    movie.save()

    documents_unpublished = index.prepare_documents(MoviePage, [movie])
    assert len(documents_unpublished) == 0, (
        "Should NOT create document for unpublished page - "
        "this proves _process_model_instance filters correctly"
    )
