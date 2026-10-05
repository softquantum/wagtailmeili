from unittest.mock import Mock

import pytest
from django.db import models
from requests import Response
from wagtail.search import index as wagtail_index
from wagtail.models import AbstractPage, Page
from wagtailmeili.index import MeilisearchIndex, IndexOperationStatus
from wagtailmeili.testapp.models import MoviePage, MoviePageWithManager, NonIndexedModel
from meilisearch.errors import MeilisearchApiError


def test_skip_unpublished_pages(meilisearch_backend, load_movies_data):
    """Test that unpublished pages are skipped during indexing."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)
    movie = MoviePage.objects.first()
    movie.live = False

    documents = meili_index.prepare_documents(MoviePage, [movie])
    assert len(documents) == 0


def test_skip_unpublished_pages_with_custom_base_page_model(meilisearch_backend):
    """Test that unpublished pages inheriting from a custom base page model are skipped."""
    meili_index = MeilisearchIndex(meilisearch_backend, MoviePage)
    custom_page = Mock(spec=AbstractPage)
    custom_page.id = 1
    custom_page.live = False

    assert not isinstance(custom_page, Page)
    assert meili_index._should_skip(custom_page, MoviePage) is True


@pytest.mark.django_db
def test_skip_by_field_value_of_concrete_model_applies_to_its_proxy(meilisearch_backend, movies_index_page):
    """Test that a field value rule set on a model also skips items indexed through its proxy."""
    jedi = movies_index_page.add_child(instance=MoviePage(title="Return of the Jedi", slug="return-of-the-jedi"))
    other = movies_index_page.add_child(instance=MoviePage(title="Star Wars", slug="star-wars"))
    index = meilisearch_backend.get_index_for_model(MoviePageWithManager)

    documents = index.prepare_documents(MoviePageWithManager, [jedi, other])

    assert [document["id"] for document in documents] == [other.pk]


@pytest.mark.django_db
def test_skip_by_field_value_of_proxy_does_not_apply_to_concrete_model(meilisearch_backend, movies_index_page):
    """Test that a field value rule set on a proxy only skips items indexed through that proxy."""
    movie = movies_index_page.add_child(instance=MoviePage(title="Star Wars", slug="star-wars"))
    meilisearch_backend.skip_models_by_field_value = {
        "wagtailmeili_testapp.moviepagewithmanager": {"field": "title", "value": "Star Wars"}
    }
    proxy_index = meilisearch_backend.get_index_for_model(MoviePageWithManager)
    concrete_index = meilisearch_backend.get_index_for_model(MoviePage)

    assert proxy_index.prepare_documents(MoviePageWithManager, [movie]) == []
    assert [document["id"] for document in concrete_index.prepare_documents(MoviePage, [movie])] == [movie.pk]


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

    status = index._is_not_indexable(SkippedModel)
    assert status == IndexOperationStatus.SKIPPED


def test_validate_page_model_skipped(meilisearch_backend):
    """Test model validation when a Page is in skip_models list."""

    class SkippedPage(Page):

        class Meta:
            app_label = 'wagtailmeili'

    meilisearch_backend.skip_models = ['wagtailmeili.skippedpage']
    index = MeilisearchIndex(meilisearch_backend, SkippedPage)

    status = index._is_not_indexable(SkippedPage)
    assert status == IndexOperationStatus.SKIPPED


def test_validate_model_not_indexed(meilisearch_backend):
    """Test model validation when model is not indexed."""

    class UnindexedModel(models.Model):
        pass

    index = MeilisearchIndex(meilisearch_backend, UnindexedModel)
    status = index._is_not_indexable(UnindexedModel)
    assert status == IndexOperationStatus.IS_NOT_INDEXED


def test_error_handling_settings_update(meilisearch_backend, monkeypatch):
    """Test error handling during settings update."""

    def mock_update_settings(*args, **kwargs):
        raise MeilisearchApiError("Settings update error")

    index = MeilisearchIndex(meilisearch_backend, MoviePage)
    monkeypatch.setattr(index.index, "update_settings", mock_update_settings)

    task_info = index.update_index_settings()
    assert task_info is None


def test_add_model_is_not_indexed(meilisearch_backend):
    """Test add_model when the model is not indexed."""

    index = MeilisearchIndex(meilisearch_backend, NonIndexedModel)
    result = index.add_model(NonIndexedModel)
    assert result is None


def test_add_model_error_handling(meilisearch_backend, monkeypatch):
    """Test error handling when creating an index fails."""

    def mock_create_index(*args, **kwargs):
        response = Response()
        response.status_code = 400
        response._content = b'{"message": "Test error", "code": "index_creation_failed"}'
        raise MeilisearchApiError("Test error message", response)

    def mock_is_in_meilisearch(*args, **kwargs):
        return False

    monkeypatch.setattr(meilisearch_backend.client, "create_index", mock_create_index)
    monkeypatch.setattr("wagtailmeili.index.is_in_meilisearch", mock_is_in_meilisearch)
    index = MeilisearchIndex(meilisearch_backend, MoviePage)

    result = index.add_model(MoviePage)
    assert result is None
