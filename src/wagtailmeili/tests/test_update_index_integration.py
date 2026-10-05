"""The update_index management command against a real Meilisearch instance."""
import pytest
from django.core.management import call_command

from wagtailmeili.testapp.models import MoviePage, ReviewPage

REVIEW_INDEX = "wagtailmeili_testapp_reviewpage"


@pytest.fixture
def pages(movies_index_page, clean_meilisearch_index):
    """Create a live movie, a draft movie and a page of a model listed in SKIP_MODELS."""
    live = movies_index_page.add_child(instance=MoviePage(title="Star Wars", slug="star-wars"))
    movies_index_page.add_child(instance=MoviePage(title="Draft movie", slug="draft-movie", live=False))
    movies_index_page.add_child(instance=ReviewPage(title="A review", slug="a-review"))
    return live


def index_uids(backend):
    return {index.uid for index in backend.client.get_indexes({"limit": 1000})["results"]}


@pytest.mark.django_db
def test_update_index_with_skip_models_indexes_only_live_pages_of_unskipped_models(
    meilisearch_backend, pages, wait_for_meilisearch
):
    call_command("update_index", backend_name="meilisearch", verbosity=0)
    wait_for_meilisearch()

    movie_index = meilisearch_backend.get_index_for_model(MoviePage)
    assert movie_index.get_document_ids() == {str(pages.pk)}
    uids = index_uids(meilisearch_backend)
    assert REVIEW_INDEX not in uids
    assert not [uid for uid in uids if uid.endswith("_new")]


@pytest.mark.django_db
def test_update_index_rerun_replaces_existing_index_content(meilisearch_backend, pages, wait_for_meilisearch):
    call_command("update_index", backend_name="meilisearch", verbosity=0)
    wait_for_meilisearch()
    movie_index = meilisearch_backend.get_index_for_model(MoviePage)
    movie_index.index.add_documents([{"id": 900001, "title": "orphan"}])
    wait_for_meilisearch()
    assert movie_index.get_document_ids() == {str(pages.pk), "900001"}

    call_command("update_index", backend_name="meilisearch", verbosity=0)
    wait_for_meilisearch()

    assert movie_index.get_document_ids() == {str(pages.pk)}
    assert not [uid for uid in index_uids(meilisearch_backend) if uid.endswith("_new")]
