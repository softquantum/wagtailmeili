import pytest
from unittest.mock import Mock
from meilisearch.errors import MeilisearchApiError
from requests import HTTPError
from requests import Response

from wagtailmeili.testapp.models import MoviePage
from wagtailmeili.utils import (
    model_is_skipped,
    check_for_task_successful_completion,
    is_in_meilisearch,
    transform_to_int
)


class TestModelIsSkipped:

    def test_empty_skip_models(self):
        """Test with empty skip_models list"""
        assert model_is_skipped(MoviePage, []) is False

    def test_model_in_skip_models(self):
        """Test with model in skip_models list"""
        skip_models = ['wagtailmeili_testapp.MoviePage']
        assert model_is_skipped(MoviePage, skip_models) is True

    def test_model_not_in_skip_models(self):
        """Test with model not in skip_models list"""
        skip_models = ['other_app.OtherModel']
        assert model_is_skipped(MoviePage, skip_models) is False

    def test_skip_models_case_variants(self):
        """Test with various case variations in skip_models"""
        variants = [
            ['WAGTAILMEILI_TESTAPP.moviepage'],
            ['Wagtailmeili_TestApp.moviePage'],
            ['wagtailmeili_testapp.MoviePage'],
            ['WAGTAILMEILI_TESTAPP.MOVIEPAGE']
        ]
        for skip_models in variants:
            assert model_is_skipped(MoviePage, skip_models) is True

    def test_invalid_input_cases(self):
        """Test various invalid inputs that should raise TypeError"""
        invalid_inputs = [
            ("string", "Not a class at all"),
            (dict, "A class but not a Model subclass"),
            (object(), "An instance, not a class"),
            (type("DynamicClass", (), {}), "A dynamic class but not a Model subclass"),
            (None, "None value")
        ]

        for invalid_input, case_description in invalid_inputs:
            with pytest.raises(TypeError, match="Expected a Django/Wagtail Model class"):
                model_is_skipped(invalid_input, ["appname.model"])


class TestCheckForTaskSuccessfulCompletion:
    @pytest.fixture
    def mock_client(self):
        return Mock()

    def test_successful_completion(self, mock_client):
        """Test successful task completion"""
        mock_client.get_task.return_value.status = "succeeded"

        result = check_for_task_successful_completion(mock_client, "task_id")

        assert result is True
        mock_client.get_task.assert_called_with("task_id")

    def test_failed_completion(self, mock_client):
        """Test failed task completion"""
        mock_client.get_task.return_value.status = "failed"

        result = check_for_task_successful_completion(mock_client, "task_id")

        assert result is False
        mock_client.get_task.assert_called_with("task_id")

    def test_timeout(self, mock_client):
        """Test task timeout"""
        mock_client.get_task.return_value.status = "processing"

        result = check_for_task_successful_completion(mock_client, "task_id", timeout=0.1)

        assert result is False
        assert mock_client.get_task.called


class TestIsInMeilisearch:
    @pytest.fixture
    def mock_client(self):
        return Mock()

    def test_index_exists(self, mock_client):
        """Test when index exists"""
        mock_client.get_index.return_value = Mock()

        assert is_in_meilisearch(mock_client, "test_index") is True
        mock_client.get_index.assert_called_once_with("test_index")

    def test_index_not_exists_meilisearch_error(self, mock_client):
        """Test when index doesn't exist (MeilisearchApiError)"""
        # Create a mock response
        response = Response()
        response.status_code = 400
        response._content = b'{"message": "Test error", "code": "index_creation_failed"}'

        # Create MeilisearchApiError with the mock response
        error = MeilisearchApiError("Index not found", response)
        mock_client.get_index.side_effect = error

        assert is_in_meilisearch(mock_client, "test_index") is False
        mock_client.get_index.assert_called_once_with("test_index")

    def test_index_not_exists_http_error(self, mock_client):
        """Test when index doesn't exist (HTTPError)"""
        mock_client.get_index.side_effect = HTTPError("HTTP Error")

        assert is_in_meilisearch(mock_client, "test_index") is False
        mock_client.get_index.assert_called_once_with("test_index")


class TestTransformToInt:
    def test_string_to_int(self):
        """Test converting string to int"""
        assert transform_to_int("123") == 123
        assert transform_to_int("abc") == "abc"  # Non-numeric string returns as is

    def test_list_to_int(self):
        """Test converting list of strings to int"""
        input_list = ["123", "456", "abc"]
        expected = [123, 456]
        assert transform_to_int(input_list) == expected

    def test_nested_list_to_int(self):
        """Test converting nested list of strings to int"""
        input_list = [["123", "456"], ["789", "abc"]]
        expected = [123, 456, 789]
        assert transform_to_int(input_list) == expected

    def test_mixed_content_list(self):
        """Test list with mixed content"""
        input_list = ["123", "abc", "456"]
        expected = [123, 456]
        assert transform_to_int(input_list) == expected

    def test_non_string_input(self):
        """Test with non-string input"""
        assert transform_to_int(123) == 123  # Number returns as is
        assert transform_to_int(None) is None  # None returns as is

    def test_empty_list(self):
        """Test with empty list"""
        assert transform_to_int([]) == []

    def test_nested_list_with_invalid_items(self):
        """Test nested list with items that can't have isdigit called"""
        input_list = [[123, None], ["456", "abc"]]
        expected = [[123, None], ["456", "abc"]]  # Returns original list due to AttributeError
        assert transform_to_int(input_list) == expected

    def test_nested_list_all_strings(self):
        """Test nested list with all string items"""
        input_list = [["123", "456"], ["789", "012"]]
        expected = [123, 456, 789, 12]  # All valid string numbers are converted to a flat list
        assert transform_to_int(input_list) == expected