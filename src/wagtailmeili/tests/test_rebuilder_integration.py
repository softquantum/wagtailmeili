"""Tests for the MeilisearchRebuilder"""
from unittest.mock import patch

import pytest

from wagtailmeili.index import MeilisearchIndex
from wagtailmeili.rebuilder import MeilisearchRebuilder
from wagtailmeili.testapp.models import MoviePage
from wagtailmeili.utils import is_in_meilisearch, check_for_task_successful_completion


def test_start_with_existing_index(meilisearch_rebuilder):
    """Test the start method when an index already exists."""
    index = meilisearch_rebuilder.index
    original_name = "existing_index"
    index.name = original_name
    # Create the index in meilisearch
    task = index.client.create_index(original_name)
    index.client.wait_for_task(task.task_uid)

    # Start the rebuilder that will check if the index exists and create a new one
    new_index = meilisearch_rebuilder.start()
    assert new_index.name == f"{original_name}_new"
    index.client.delete_index(new_index.name)


def test_start_without_existing_index(meilisearch_rebuilder):
    """Test the start method when an index does not exist."""
    index = meilisearch_rebuilder.index
    index.name = "non_existing_index"

    # Delete the index if it exists (from previous tests)
    if is_in_meilisearch(index.client, index.name):
        index.client.delete_index(index.name)

    new_index = meilisearch_rebuilder.start()

    assert new_index.name == "non_existing_index"
    # We got only a reference so the index should not be created in meilisearch
    assert not is_in_meilisearch(index.client, new_index.name)


def test_start_with_error(meilisearch_rebuilder):
    """Test the start method when an error occurs."""
    index = meilisearch_rebuilder.index

    # Force an error by making client.index raise an exception
    with patch.object(index.client, 'index', side_effect=Exception('Mocked error')):
        new_index = meilisearch_rebuilder.start()
        assert new_index == index


def test_finish_with_swap(meilisearch_rebuilder):
    """Test the finish method with successful swap."""
    index = meilisearch_rebuilder.index
    original_name = "existing_index"
    index._name = original_name

    # Create both indexes
    task = index.client.create_index(original_name)
    index.client.wait_for_task(task.task_uid)
    task = index.client.create_index(f"{original_name}_new")
    index.client.wait_for_task(task.task_uid)

    assert is_in_meilisearch(index.client, original_name)
    assert is_in_meilisearch(index.client, f"{original_name}_new")

    task = meilisearch_rebuilder.finish()

    assert task is not None
    assert hasattr(task, 'task_uid')
    succeeded = check_for_task_successful_completion(index.client, task.task_uid, timeout=100)
    assert succeeded is True

# def test_reset_index(meilisearch_rebuilder, test_movies):
#     """Test reset_index method by ensuring all documents are deleted."""
#     index: MeilisearchIndex = meilisearch_rebuilder.index
#
#     task = index.add_items(MoviePage, test_movies)
#     index.client.wait_for_task(task.task_uid)
#
#     # assert index has these docs
#     documents = index.client.index(index.name).get_documents()
#     assert documents.total == 2
#
#     # reset the index
#     MeilisearchRebuilder.reset_index(index)
#
#     # assert the index is empty
#     documents = index.client.index(index.name).get_documents()
#     assert documents.total == 0
