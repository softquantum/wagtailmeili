"""Stale document cleanup against a real Meilisearch instance."""
from io import StringIO

import pytest
from django.core.management import call_command

from wagtailmeili.rebuilder import MeilisearchRebuilder
from wagtailmeili.testapp.models import MoviePage

ORPHAN_IDS = {900001, 900002}


@pytest.fixture
def movie_index(meilisearch_backend, movies_index_page, clean_meilisearch_index, wait_for_meilisearch):
    """Index three live movies, then add two orphan documents and one for a draft page."""
    live_movies = [
        movies_index_page.add_child(instance=MoviePage(title=f"Live movie {i}", slug=f"live-movie-{i}"))
        for i in range(3)
    ]
    draft = movies_index_page.add_child(instance=MoviePage(title="Draft movie", slug="draft-movie", live=False))

    index = meilisearch_backend.get_index_for_model(MoviePage)
    index.add_model(MoviePage)
    index.add_items(MoviePage, live_movies)
    stale_ids = ORPHAN_IDS | {draft.pk}
    index.index.add_documents([{"id": stale_id, "title": "stale"} for stale_id in stale_ids])
    wait_for_meilisearch()

    live_ids = {str(movie.pk) for movie in live_movies}
    assert index.get_document_ids() == live_ids | {str(stale_id) for stale_id in stale_ids}
    return index, live_ids


@pytest.mark.django_db
def test_get_document_ids_returns_every_document(meilisearch_backend, clean_meilisearch_index, wait_for_meilisearch):
    index = meilisearch_backend.get_index_for_model(MoviePage)
    index.add_model(MoviePage)
    index.index.add_documents([{"id": i, "title": f"movie {i}"} for i in range(1, 1006)])
    wait_for_meilisearch()

    assert index.get_document_ids() == {str(i) for i in range(1, 1006)}


@pytest.mark.django_db
def test_cleanup_stale_documents_keeps_only_live_documents(movie_index, wait_for_meilisearch):
    index, live_ids = movie_index

    index.cleanup_stale_documents(live_ids)
    wait_for_meilisearch()

    assert index.get_document_ids() == live_ids


@pytest.mark.django_db
def test_rebuild_index_for_model_keeps_only_live_documents(movie_index, wait_for_meilisearch):
    index, live_ids = movie_index

    MeilisearchRebuilder(index).rebuild_index_for_model(MoviePage)
    wait_for_meilisearch()

    assert index.get_document_ids() == live_ids


@pytest.mark.django_db
def test_cleanup_command_deletes_stale_documents(movie_index, wait_for_meilisearch):
    index, live_ids = movie_index
    out = StringIO()

    call_command("cleanup_search_index", backend="meilisearch", model="wagtailmeili_testapp.MoviePage", stdout=out)
    wait_for_meilisearch()

    assert "Deleted 3 stale documents from MoviePage index" in out.getvalue()
    assert "Successfully cleaned 3 stale documents." in out.getvalue()
    assert index.get_document_ids() == live_ids


@pytest.mark.django_db
def test_cleanup_command_dry_run_deletes_nothing(movie_index, wait_for_meilisearch):
    index, live_ids = movie_index
    ids_before = index.get_document_ids()
    out = StringIO()

    call_command(
        "cleanup_search_index", backend="meilisearch", model="wagtailmeili_testapp.MoviePage", dry_run=True, stdout=out
    )
    wait_for_meilisearch()

    assert "Would delete 3 stale documents from MoviePage index" in out.getvalue()
    assert "Dry run complete. Would have cleaned 3 stale documents." in out.getvalue()
    assert index.get_document_ids() == ids_before


@pytest.mark.django_db
def test_cleanup_command_reports_no_stale_documents(movie_index, wait_for_meilisearch):
    index, live_ids = movie_index
    index.cleanup_stale_documents(live_ids)
    wait_for_meilisearch()
    out = StringIO()

    call_command("cleanup_search_index", backend="meilisearch", model="wagtailmeili_testapp.MoviePage", stdout=out)

    assert "No stale documents found for MoviePage" in out.getvalue()
    assert "Successfully cleaned 0 stale documents." in out.getvalue()
    assert index.get_document_ids() == live_ids


@pytest.mark.django_db
def test_cleanup_command_for_all_models_skips_models_in_skip_models(movie_index, wait_for_meilisearch):
    index, live_ids = movie_index
    out = StringIO()

    call_command("cleanup_search_index", backend="meilisearch", stdout=out)
    wait_for_meilisearch()

    assert "No index found for ReviewPage, skipping" in out.getvalue()
    assert "NullIndex" not in out.getvalue()
    assert "Deleted 3 stale documents from MoviePage index" in out.getvalue()
    assert index.get_document_ids() == live_ids
