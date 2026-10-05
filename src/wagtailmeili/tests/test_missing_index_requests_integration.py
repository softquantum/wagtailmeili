"""Models without an index must not generate Meilisearch requests.

Regression tests for https://github.com/softquantum/wagtailmeili/issues/2
"""
from io import StringIO

import pytest
from django.core.management import call_command
from wagtail.models import ReferenceIndex

from wagtailmeili.index import NullIndex
from wagtailmeili.testapp.models import MoviePage, NonIndexedModel, NonIndexedPage, ReviewPage

MOVIE_INDEX = "wagtailmeili_testapp_moviepage"
REVIEW_INDEX = "wagtailmeili_testapp_reviewpage"
NON_INDEXED_PAGE_INDEX = "wagtailmeili_testapp_nonindexedpage"


def requests_for(index_name, sent):
    return [request for request in sent if f"/indexes/{index_name}/" in request or request.endswith(index_name)]


@pytest.mark.django_db
def test_indexed_model_sends_requests(movies_index_page, clean_meilisearch_index, meilisearch_requests):
    """Control: the recorder sees the requests of a model that is indexed."""
    meilisearch_requests.clear()

    movies_index_page.add_child(instance=MoviePage(title="Star Wars", slug="star-wars"))

    assert f"POST /indexes/{MOVIE_INDEX}/documents" in meilisearch_requests


@pytest.mark.django_db
def test_non_indexed_model_sends_no_requests(meilisearch_backend, clean_meilisearch_index, meilisearch_requests):
    meilisearch_requests.clear()

    instance = NonIndexedModel.objects.create()
    meilisearch_backend.add(instance)
    meilisearch_backend.delete(instance)
    instance.delete()

    assert meilisearch_requests == []


@pytest.mark.django_db
def test_wagtail_internal_model_index_sends_no_requests(meilisearch_backend, meilisearch_requests):
    meilisearch_requests.clear()

    index = meilisearch_backend.get_index_for_model(ReferenceIndex)
    index.delete_item(1)

    assert isinstance(index, NullIndex)
    assert meilisearch_requests == []


@pytest.mark.django_db
def test_non_indexed_page_lifecycle_sends_no_requests_for_its_index(movies_index_page, clean_meilisearch_index, meilisearch_requests):
    meilisearch_requests.clear()

    page = movies_index_page.add_child(instance=NonIndexedPage(title="Plain", slug="plain"))
    page.unpublish()
    page.delete()

    assert requests_for(NON_INDEXED_PAGE_INDEX, meilisearch_requests) == []


@pytest.mark.django_db
def test_skipped_model_lifecycle_sends_no_requests_for_its_index(movies_index_page, clean_meilisearch_index, meilisearch_requests):
    meilisearch_requests.clear()

    review = movies_index_page.add_child(instance=ReviewPage(title="A review", slug="a-review"))
    review.unpublish()
    review.delete()

    assert requests_for(REVIEW_INDEX, meilisearch_requests) == []


@pytest.mark.django_db
def test_update_index_sends_no_requests_for_skipped_model(
    movies_index_page, clean_meilisearch_index, meilisearch_requests, wait_for_meilisearch
):
    movies_index_page.add_child(instance=MoviePage(title="Star Wars", slug="star-wars"))
    movies_index_page.add_child(instance=ReviewPage(title="A review", slug="a-review"))
    wait_for_meilisearch()
    meilisearch_requests.clear()

    call_command("update_index", backend_name="meilisearch", verbosity=0)

    assert requests_for(MOVIE_INDEX, meilisearch_requests)
    assert requests_for(REVIEW_INDEX, meilisearch_requests) == []


@pytest.mark.django_db
def test_cleanup_command_sends_no_requests_for_skipped_model(
    movies_index_page, clean_meilisearch_index, meilisearch_requests
):
    movies_index_page.add_child(instance=ReviewPage(title="A review", slug="a-review"))
    meilisearch_requests.clear()

    call_command(
        "cleanup_search_index", backend="meilisearch", model="wagtailmeili_testapp.ReviewPage", stdout=StringIO()
    )

    assert meilisearch_requests == []
