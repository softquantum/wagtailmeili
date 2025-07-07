import logging

import pytest
from unittest.mock import MagicMock, patch
from wagtailmeili.results import MeilisearchEmptySearchResults
from wagtailmeili.backend import MeilisearchBackend
from wagtailmeili.exceptions import MeiliSearchConnectionException
from wagtailmeili.query_compiler import MeilisearchQueryCompiler, MeilisearchAutocompleteQueryCompiler
from wagtailmeili.rebuilder import MeilisearchRebuilder
from wagtailmeili.testapp.models import MoviePage, NonIndexedModel, NonIndexedPage

logger = logging.getLogger(__name__)


@patch("wagtailmeili.backend.Client")
def test_backend_wraps_connection_errors(mock_client, meilisearch_params):
    """Test that various connection errors are properly handled."""
    def _test_error(error_type, error_msg):
        mock_client.side_effect = error_type(error_msg)
        with pytest.raises(MeiliSearchConnectionException) as exc_info:
            MeilisearchBackend(meilisearch_params)
        assert str(error_msg) in str(exc_info.value)
        mock_client.side_effect = None

    _test_error(ConnectionRefusedError, "Connection refused")
    _test_error(TimeoutError, "Connection timed out")
    _test_error(ValueError, "Invalid URL format")


@patch("wagtailmeili.backend.Client")
def test_backend_initializes_client_with_correct_params(mock_client, meilisearch_params):
    """Test that the client is initialized with the correct URL and key."""
    MeilisearchBackend(meilisearch_params)
    mock_client.assert_called_once_with(
        "http://localhost:7700",
        "test_key"
    )


def test_backend_sets_optional_parameters(meilisearch_params):
    """Test that optional parameters are properly set."""
    custom_stop_words = ["test", "words", "here"]
    meilisearch_params["STOP_WORDS"] = custom_stop_words
    backend = MeilisearchBackend(meilisearch_params)
    assert backend.stop_words == custom_stop_words


def test_skip_models_validation(meilisearch_params):
    """Test various invalid skip_models configurations."""
    meilisearch_params["SKIP_MODELS"] = [123]
    with pytest.raises(ValueError, match="SKIP_MODELS entries must be strings"):
        MeilisearchBackend(meilisearch_params)

    meilisearch_params["SKIP_MODELS"] = ["invalid_format"]
    with pytest.raises(ValueError, match="Invalid skip_models entry"):
        MeilisearchBackend(meilisearch_params)

    meilisearch_params["SKIP_MODELS"] = [".ModelName"]
    with pytest.raises(ValueError, match="Invalid skip_models entry"):
        MeilisearchBackend(meilisearch_params)

    meilisearch_params["SKIP_MODELS"] = ["wagtailmeili_testapp."]
    with pytest.raises(ValueError, match="Invalid skip_models entry"):
        MeilisearchBackend(meilisearch_params)


def test_query_compiler_class_assignment():
    """Test that the correct query compiler classes are used."""
    backend = MeilisearchBackend({"HOST": "dummy", "PORT": "dummy", "MASTER_KEY": "dummy"})
    assert backend.query_compiler_class == MeilisearchQueryCompiler
    assert backend.autocomplete_query_compiler_class == MeilisearchAutocompleteQueryCompiler


def test_get_rebuilder():
    """Test that get_rebuilder returns the correct rebuilder class."""
    backend = MeilisearchBackend({"HOST": "dummy", "PORT": "dummy", "MASTER_KEY": "dummy"})
    assert backend.get_rebuilder() == MeilisearchRebuilder


def test_get_empty_rebuilder_when_no_rebuilder_class(meilisearch_backend):
    """Test get_rebuilder when rebuilder_class is None."""
    meilisearch_backend.rebuilder_class = None
    assert meilisearch_backend.get_rebuilder() is None


def test_skip_models_by_field_value_empty(meilisearch_params):
    """Test _get_skipped_models_by_field_value with empty input."""
    meilisearch_params["SKIP_MODELS_BY_FIELD_VALUE"] = {}
    backend = MeilisearchBackend(meilisearch_params)
    assert backend.skip_models_by_field_value == {}


@patch.object(MeilisearchRebuilder, "reset_index", side_effect=Exception("Rebuilder object does not have a 'reset_index' method."))
def test_reset_index_error_handling(mock_reset_index, meilisearch_backend):
    """Test reset_index error handling when rebuilder lacks method."""
    with pytest.raises(Exception, match="MeilisearchRebuilder does not implement 'reset_index'."):
        meilisearch_backend.reset_index()


@patch.object(MeilisearchRebuilder, "delete_all_indexes", side_effect=Exception("Rebuilder object does not have a 'delete_all_indexes' method."))
def test_delete_all_indexes_error_handling(mock_reset_index, meilisearch_backend):
    """Test reset_index error handling when rebuilder lacks method."""
    with pytest.raises(Exception, match="MeilisearchRebuilder does not implement a 'delete_all_indexes'."):
        meilisearch_backend.delete_all_indexes()


def test_search_non_indexed_models(meilisearch_backend):
    """Test _search with a model class that doesn't inherit from Indexed."""
    results = meilisearch_backend.search("query", NonIndexedModel)
    assert isinstance(results, MeilisearchEmptySearchResults)

    results = meilisearch_backend.search("query", NonIndexedPage)
    assert isinstance(results, MeilisearchEmptySearchResults)


@pytest.mark.django_db
def test_backend_search(meilisearch_backend, load_movies_data):
    """Test the search method of the backend."""
    mock_index = MagicMock()
    mock_index.search.return_value = {"hits": [{"id": 11}], "totalHits": 1}
    meilisearch_backend.client.index = MagicMock(return_value=mock_index)
    results = meilisearch_backend.search("Star Wars", MoviePage.objects.all())
    actual_hits = results.get()["hits"]
    expected_hits = mock_index.search.return_value["hits"]

    assert len(actual_hits) == len(expected_hits)
    for result, expected in zip(actual_hits, expected_hits):
        assert result["id"] == expected["id"]


@pytest.mark.django_db
def test_returns_empty_search_results_for_non_indexed_class(meilisearch_backend):
    model = NonIndexedModel
    queryset = model.objects.all()
    query = "test query"
    result = meilisearch_backend._search(MeilisearchQueryCompiler, query, queryset)
    assert isinstance(result, MeilisearchEmptySearchResults)

    model = NonIndexedPage
    queryset = model.objects.all()
    query = "test query"
    result = meilisearch_backend._search(MeilisearchQueryCompiler, query, queryset)
    assert isinstance(result, MeilisearchEmptySearchResults)