import pytest
from unittest.mock import Mock
from wagtailmeili.results import MeilisearchResults, MeilisearchEmptySearchResults
from wagtail.search.backends.base import FilterFieldError


class TestMeilisearchResults:
    def test_supports_facet(self):
        assert MeilisearchResults.supports_facet is True

    @pytest.mark.parametrize("results,expected_count", [
        ({"totalHits": 5}, 5),
        ({"estimatedTotalHits": 10}, 10),
        # When there's no totalHits or estimatedTotalHits, it falls back to len(results)
        ({"key1": 1, "key2": 2, "key3": 3}, 3),
    ])
    def test_get_results_count(self, results, expected_count):
        # Create a temporary instance just for testing get_results_count
        count = MeilisearchResults.get_results_count(None, results)
        assert count == expected_count

    @pytest.fixture
    def mock_backend(self):
        backend = Mock()
        backend.client.index.return_value.search.return_value = {
            "hits": [{"id": "1"}, {"id": "2"}],
            "totalHits": 2
        }
        return backend

    @pytest.fixture
    def mock_query_compiler(self):
        compiler = Mock()
        compiler.get_query.return_value = "test query"
        compiler.queryset.model._meta.label = "test_app.TestModel"
        compiler.queryset.model = Mock()
        compiler.opt_params = None  # or {}
        return compiler

    @pytest.fixture
    def mock_search_field(self):
        """Create a mock search field"""
        field = Mock()
        field.field_name = "test_field"
        return field

    def test_results_caching(self, mock_backend, mock_query_compiler):
        # Set up
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # First call
        first_results = search_results._do_search()
        assert search_results._results_cache == first_results
        assert search_results._count_cache == 2

        # Modify the mock's return value
        mock_backend.client.index.return_value.search.return_value = {
            "hits": [{"id": "3"}, {"id": "4"}],
            "totalHits": 4
        }

        # Second call should get new results
        second_results = search_results._do_search()
        assert second_results != first_results
        assert search_results._results_cache == second_results
        assert search_results._count_cache == 4

    def test_do_search_cached_results(self, mock_backend, mock_query_compiler):
        # Set up
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Manually set up the cache to simulate a previous search
        search_results._results_cache = {
            "hits": [{"id": "1"}, {"id": "2"}],
            "totalHits": 2,
            "pks": [1, 2],
            "model": mock_query_compiler.queryset.model._meta.label
        }
        search_results._count_cache = 2

        # Call _do_search which should use the cache
        results = search_results._do_search()

        # Verify we got the cached results
        assert results == search_results._results_cache

    def test_do_search_with_different_result_structure(self, mock_backend, mock_query_compiler):
        # Set up mock with different result structure
        mock_backend.client.index.return_value.search.return_value = {
            "hits": [{"id": "1"}, {"id": "2"}],
            "estimatedTotalHits": 100
        }

        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        results = search_results._do_search()

        assert search_results._count_cache == 100
        assert results["pks"] == [1, 2]

    def test_do_search_with_custom_opt_params(self, mock_backend, mock_query_compiler):
        # Set up
        custom_opt_params = {
            "limit": 5,
            "offset": 10,
            "showMatchesPosition": False
        }

        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )
        search_results.opt_params.update(custom_opt_params)

        search_results._do_search()

        # Verify search was called with custom params
        mock_backend.client.index.return_value.search.assert_called_once_with(
                query="test query",
                opt_params=search_results.opt_params
        )

    def test_do_count_empty_cache(self, mock_backend, mock_query_compiler):
        """Test _do_count when cache is empty (_count_cache is None)"""
        # Set up
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Ensure cache is empty
        search_results._count_cache = None

        # Get count
        count = search_results._do_count()

        # Verify _do_search was called to populate cache
        mock_backend.client.index.return_value.search.assert_called_once()

        # Verify correct count was returned
        assert count == 2  # Based on our mock setup returning totalHits: 2
        assert search_results._count_cache == 2

    def test_do_count_with_cached_value(self, mock_backend, mock_query_compiler):
        """Test _do_count when cache already has a value"""
        # Set up
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Pre-set the cache
        search_results._count_cache = 42

        # Get count
        count = search_results._do_count()

        # Verify _do_search was NOT called
        mock_backend.client.index.return_value.search.assert_not_called()

        # Verify cached count was returned
        assert count == 42
        assert search_results._count_cache == 42

    def test_facet_successful(self, mock_backend, mock_query_compiler, mock_search_field):
        """Test successful facet retrieval"""
        # Set up the mock query compiler with _get_filterable_field
        mock_query_compiler._get_filterable_field.return_value = mock_search_field
        mock_query_compiler.query.query_string = "test query"

        # Set up the mock index response with facet distribution
        facet_response = {
            "facetDistribution": {
                "test_field": {
                    "value1": 10,
                    "value2": 5,
                    "value3": 2
                }
            }
        }
        mock_backend.client.index.return_value.search.return_value = facet_response

        # Create search results instance
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Call facet
        result = search_results.facet("test_field")

        # Verify the search call
        mock_backend.client.index.return_value.search.assert_called_once_with(
                query="test query",
                opt_params={
                    "facets": ["test_field"],
                }
        )

        # Verify the result is an OrderedDict with correct values in descending order
        assert list(result.items()) == [
            ("value1", 10),
            ("value2", 5),
            ("value3", 2)
        ]

    def test_facet_field_not_filterable(self, mock_backend, mock_query_compiler):
        """Test facet with non-filterable field"""
        # Set up a mock model with a name
        mock_model = Mock()
        mock_model.__name__ = 'TestModel'

        # Set up the mock query compiler
        mock_query_compiler._get_filterable_field.return_value = None
        mock_query_compiler.queryset.model = mock_model

        # Create search results instance
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Test that attempting to facet on non-filterable field raises error
        with pytest.raises(FilterFieldError) as exc_info:
            search_results.facet("invalid_field")

        # Verify error message
        expected_message = (
            'Cannot facet search results with field "invalid_field". '
            'Please add index.FilterField(\'invalid_field\') to TestModel.search_fields.'
        )
        assert str(exc_info.value) == expected_message
        assert exc_info.value.field_name == "invalid_field"

    def test_facet_empty_distribution(self, mock_backend, mock_query_compiler, mock_search_field):
        """Test facet when no distribution is returned"""
        # Set up the mock query compiler
        mock_query_compiler._get_filterable_field.return_value = mock_search_field
        mock_query_compiler.query.query_string = "test query"

        # Set up mock response with no facet distribution
        mock_backend.client.index.return_value.search.return_value = {
            "facetDistribution": {
                "test_field": {}  # Empty distribution
            }
        }

        # Create search results instance
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Call facet
        result = search_results.facet("test_field")

        # Verify result is an empty OrderedDict
        assert len(result) == 0

    def test_facet_missing_distribution(self, mock_backend, mock_query_compiler, mock_search_field):
        """Test facet when facetDistribution is missing from response"""
        # Set up the mock query compiler
        mock_query_compiler._get_filterable_field.return_value = mock_search_field
        mock_query_compiler.query.query_string = "test query"

        # Set up mock response with no facetDistribution
        mock_backend.client.index.return_value.search.return_value = {}

        # Create search results instance
        search_results = MeilisearchResults(
                backend=mock_backend,
                query_compiler=mock_query_compiler
        )

        # Call facet
        result = search_results.facet("test_field")

        # Verify result is an empty OrderedDict
        assert len(result) == 0



class TestMeilisearchEmptySearchResults:
    def test_clone(self):
        empty_results = MeilisearchEmptySearchResults()
        cloned_results = empty_results._clone()

        assert isinstance(cloned_results, MeilisearchEmptySearchResults)
        assert empty_results is not cloned_results

    def test_do_search(self):
        empty_results = MeilisearchEmptySearchResults()
        results = empty_results._do_search()

        assert results == []

    def test_get(self):
        empty_results = MeilisearchEmptySearchResults()
        results = empty_results.get()

        assert results == []

    def test_do_count(self):
        empty_results = MeilisearchEmptySearchResults()
        count = empty_results._do_count()

        assert count == 0