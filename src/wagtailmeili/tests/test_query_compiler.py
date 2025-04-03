import logging

import pytest
from wagtail.search.query import And, Fuzzy, MatchAll, Or, Phrase, PlainText
from wagtailmeili.query_compiler import MeilisearchQueryCompiler, MeilisearchAutocompleteQueryCompiler


class TestMeilisearchQueryCompilerInitialization:
    def test_none_query_deprecation_warning(self, meilisearch_backend):
        # Using pytest's warning checker to verify the deprecation warning
        with pytest.warns(DeprecationWarning, match="Querying `None` is deprecated, use `MATCH_ALL` instead."):
            compiler = MeilisearchQueryCompiler(
                queryset=None,
                query=None,
                fields=None
            )
            # Verify that None was converted to MatchAll
            assert isinstance(compiler.query, MatchAll)


class TestMeilisearchQueryCompilerLookup:
    @pytest.fixture
    def compiler(self, meilisearch_backend):
        return MeilisearchQueryCompiler(
            queryset=None,
            query=MatchAll(),
            fields=None
        )

    def test_exact_lookup(self, compiler):
        result = compiler._process_lookup("title", "exact", "test")
        assert result == 'title:"test"'

    def test_iexact_lookup(self, compiler):
        result = compiler._process_lookup("title", "iexact", "Test")
        assert result == 'title:"test"'

    def test_contains_lookup(self, compiler):
        result = compiler._process_lookup("title", "contains", "test")
        assert result == "title:test"

    def test_in_lookup_list(self, compiler):
        result = compiler._process_lookup("title", "in", ["test1", "test2"])
        assert result == "title:test1 OR title:test2"

    def test_in_lookup_single(self, compiler):
        result = compiler._process_lookup("title", "in", "test")
        assert result == "title:test"

    def test_comparison_lookups(self, compiler):
        assert compiler._process_lookup("number", "gt", 5) == "number > 5"
        assert compiler._process_lookup("number", "gte", 5) == "number >= 5"
        assert compiler._process_lookup("number", "lt", 5) == "number < 5"
        assert compiler._process_lookup("number", "lte", 5) == "number <= 5"

    def test_range_lookup(self, compiler):
        result = compiler._process_lookup("number", "range", (1, 10))
        assert result == "number 1 TO 10"

    def test_exclude_lookup(self, compiler):
        result = compiler._process_lookup("title", "exclude", "test")
        assert result == "NOT title:test"

    def test_isnull_lookup(self, compiler):
        assert compiler._process_lookup("title", "isnull", True) == "title = NULL"
        assert compiler._process_lookup("title", "isnull", False) == "title != NULL"

    def test_startswith_lookup(self, compiler):
        result = compiler._process_lookup("title", "startswith", "test")
        assert result == "title:test*"

    def test_endswith_lookup(self, compiler):
        result = compiler._process_lookup("title", "endswith", "test")
        assert result == "title:*test"

    def test_unhandled_lookup(self, compiler, caplog):
        # Set up logging capture for the warning level
        with caplog.at_level(logging.WARNING):
            # Test with an unsupported lookup type
            result = compiler._process_lookup("title", "unsupported_lookup", "test")

            # Verify the returned value is an empty string
            assert result == ""

            # Verify the warning was logged with correct message
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == "WARNING"
            assert "Unhandled lookup: unsupported_lookup for field title" in caplog.records[0].message


class TestMeilisearchQueryCompilerFilters:
    @pytest.fixture
    def compiler(self, meilisearch_backend):
        return MeilisearchQueryCompiler(
            queryset=None,
            query=MatchAll(),
            fields=None
        )

    def test_connect_filters_and(self, compiler):
        filters = ["title:test1", "title:test2"]
        result = compiler._connect_filters(filters, "AND", False)
        assert result == "title:test1 AND title:test2"

    def test_connect_filters_or(self, compiler):
        filters = ["title:test1", "title:test2"]
        result = compiler._connect_filters(filters, "OR", False)
        assert result == "title:test1 OR title:test2"

    def test_connect_filters_negated(self, compiler):
        filters = ["title:test1", "title:test2"]
        result = compiler._connect_filters(filters, "AND", True)
        assert result == "NOT (title:test1 AND title:test2)"


class TestMeilisearchQueryCompilerCompilation:
    @pytest.fixture
    def compiler(self, meilisearch_backend):
        return MeilisearchQueryCompiler(
            queryset=None,
            query=MatchAll(),
            fields=None
        )

    def test_compile_matchall(self, compiler):
        result = compiler._compile_query(MatchAll(), None)
        assert result == ""

    def test_compile_and(self, compiler):
        query = And([PlainText("test1"), PlainText("test2")])
        result = compiler._compile_query(query, None)
        assert result == "test1 test2"

    def test_compile_or(self, compiler):
        query = Or([PlainText("test1"), PlainText("test2")])
        result = compiler._compile_query(query, None)
        assert result == "test1 test2"

    def test_compile_plaintext(self, compiler):
        query = PlainText("test")
        result = compiler._compile_query(query, None)
        assert result == "test"

    def test_compile_fuzzy(self, compiler):
        query = Fuzzy("test")
        result = compiler._compile_query(query, None)
        assert result == "test"

    def test_compile_phrase(self, compiler):
        query = Phrase("test phrase")
        result = compiler._compile_query(query, None)
        assert result == '"test phrase"'


class TestMeilisearchAutocompleteQueryCompiler:
    @pytest.fixture
    def mock_model(self):
        class MockModel:
            @staticmethod
            def get_autocomplete_search_fields():
                return [type('Field', (), {'field_name': 'title'})]
        return MockModel

    def test_init_with_fields(self, mock_model, meilisearch_backend):
        compiler = MeilisearchAutocompleteQueryCompiler(
            queryset=type('MockQuerySet', (), {'model': mock_model}),
            query=PlainText("test"),
            fields=['title']
        )
        assert compiler.searchable_fields == ['title']
        assert compiler.opt_params == {
            'attributesToSearchOn': ['title'],
            'prefix': True
        }

    def test_init_without_fields(self, mock_model, meilisearch_backend):
        compiler = MeilisearchAutocompleteQueryCompiler(
            queryset=type('MockQuerySet', (), {'model': mock_model}),
            query=PlainText("test"),
            fields=None
        )
        assert compiler.searchable_fields == ['title']
        assert compiler.opt_params == {
            'attributesToSearchOn': ['title'],
            'prefix': True
        }

    def test_get_query_matchall(self, mock_model, meilisearch_backend):
        compiler = MeilisearchAutocompleteQueryCompiler(
            queryset=type('MockQuerySet', (), {'model': mock_model}),
            query=MatchAll(),
            fields=None
        )
        assert compiler.get_query() == ""

    def test_get_query_plaintext(self, mock_model, meilisearch_backend):
        compiler = MeilisearchAutocompleteQueryCompiler(
            queryset=type('MockQuerySet', (), {'model': mock_model}),
            query=PlainText("test"),
            fields=None
        )
        assert compiler.get_query() == "test"
