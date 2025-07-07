"""Tests for the MeilisearchRebuilder"""
from unittest.mock import patch, Mock

import pytest

from wagtailmeili.exceptions import MeiliSearchRebuildException
from wagtailmeili.rebuilder import MeilisearchRebuilder
from wagtailmeili.utils import is_in_meilisearch, check_for_task_successful_completion


def test_start_with_existing_index(meilisearch_rebuilder):
    """Test the start method when an index already exists."""
    index = meilisearch_rebuilder.index
    original_name = "existing_index"
    index.name = original_name
    task = index.client.create_index(original_name)
    index.client.wait_for_task(task.task_uid)

    new_index = meilisearch_rebuilder.start()
    assert new_index.name == f"{original_name}_new"
    index.client.delete_index(new_index.name)


def test_start_with_existing_temporary_index(meilisearch_rebuilder, test_movies):
    """Test the start method when an index already exists and its temporary _new too."""
    index = meilisearch_rebuilder.index

    main_index_name = "wagtailmeili_testapp_moviepage"
    temp_index_name = f"{main_index_name}_new"

    task = index.client.create_index(main_index_name)
    index.client.wait_for_task(task.task_uid)
    assert is_in_meilisearch(index.client, main_index_name)

    task = index.client.create_index(temp_index_name)
    index.client.wait_for_task(task.task_uid)
    assert is_in_meilisearch(index.client, temp_index_name)

    documents_to_add = [
        {
            'id': movie.pk,
            'title': movie.title,
            'slug': movie.slug,
            'live': movie.live,
        }
        for movie in test_movies
    ]
    task = index.client.index(temp_index_name).add_documents(documents_to_add)
    index.client.wait_for_task(task.task_uid)

    documents = index.client.index(main_index_name).get_documents()
    documents2 = index.client.index(temp_index_name).get_documents()
    assert documents.total == 0
    assert documents2.total == 2

    index.name = main_index_name
    new_index = meilisearch_rebuilder.start()
    assert new_index.name == f"{main_index_name}_new"
    assert not is_in_meilisearch(index.client, f"{main_index_name}_new")

    index.client.delete_index(main_index_name)
    index.client.delete_index(temp_index_name)


def test_start_with_existing_temporary_index_deletion_failure(meilisearch_rebuilder, test_movies):
    """Test the start method when deletion of existing temporary index fails."""
    index = meilisearch_rebuilder.index

    main_index_name = "wagtailmeili_testapp_moviepage"
    temp_index_name = f"{main_index_name}_new"

    task = index.client.create_index(main_index_name)
    index.client.wait_for_task(task.task_uid)
    assert is_in_meilisearch(index.client, main_index_name)

    task = index.client.create_index(temp_index_name)
    index.client.wait_for_task(task.task_uid)
    assert is_in_meilisearch(index.client, temp_index_name)

    documents_to_add = [
        {
            'id': movie.pk,
            'title': movie.title,
            'slug': movie.slug,
            'live': movie.live,
        }
        for movie in test_movies
    ]
    task = index.client.index(temp_index_name).add_documents(documents_to_add)
    index.client.wait_for_task(task.task_uid)

    documents = index.client.index(main_index_name).get_documents()
    documents2 = index.client.index(temp_index_name).get_documents()
    assert documents.total == 0
    assert documents2.total == 2

    index.name = main_index_name
    with patch('wagtailmeili.rebuilder.check_for_task_successful_completion') as mock_check:
        mock_check.return_value = False

        with pytest.raises(MeiliSearchRebuildException) as excinfo:
            meilisearch_rebuilder.start()

        assert f"Failed to delete existing temporary index {temp_index_name}" in str(excinfo.value)

    index.client.delete_index(main_index_name)
    index.client.delete_index(temp_index_name)


def test_start_without_existing_index(meilisearch_rebuilder):
    """Test the start method when an index does not exist."""
    index = meilisearch_rebuilder.index
    index.name = "non_existing_index"

    # Delete the index if it exists (from previous tests)
    if is_in_meilisearch(index.client, index.name):
        index.client.delete_index(index.name)

    new_index = meilisearch_rebuilder.start()

    assert new_index.name == "non_existing_index"
    assert not is_in_meilisearch(index.client, new_index.name)


def test_start_with_error(meilisearch_rebuilder):
    """Test the start method when an error occurs during client.index call."""
    index = meilisearch_rebuilder.index
    index.name = "test_client_error_index"

    with patch.object(index.client, 'index', side_effect=Exception('Mocked error')):
        with pytest.raises(MeiliSearchRebuildException) as excinfo:
            meilisearch_rebuilder.start()

        assert "Failed to start rebuild process: Mocked error" in str(excinfo.value)


def test_start_with_error_in_getting_index(meilisearch_rebuilder):
    """Test the start method when an error occurs during get_index call."""
    index = meilisearch_rebuilder.index
    original_name = "test_error_index"
    index.name = original_name

    task = index.client.create_index(original_name)
    index.client.wait_for_task(task.task_uid)

    with patch.object(index, 'get_index', side_effect=Exception("Failed to get index")):
        with pytest.raises(MeiliSearchRebuildException) as excinfo:
            meilisearch_rebuilder.start()

        assert "Failed to start rebuild process: Failed to get index" in str(excinfo.value)

    if is_in_meilisearch(index.client, original_name):
        index.client.delete_index(original_name)


def test_finish_with_swap(meilisearch_rebuilder):
    """Test the finish method with successful swap."""
    index = meilisearch_rebuilder.index
    main_index_name = "wagtailmeili_testapp_moviepage"
    temp_index_name = "wagtailmeili_testapp_moviepage_new"
    index._name = main_index_name
    index.name = temp_index_name

    task = index.client.create_index(main_index_name)
    index.client.wait_for_task(task.task_uid)
    task = index.client.create_index(temp_index_name)
    index.client.wait_for_task(task.task_uid)

    assert is_in_meilisearch(index.client, main_index_name)
    assert is_in_meilisearch(index.client, temp_index_name)

    task = meilisearch_rebuilder.finish()
    assert task is not None
    assert task.type == "indexDeletion"
    succeeded = check_for_task_successful_completion(index.client, task.task_uid, timeout=200)
    assert succeeded is True


def test_finish_with_error(meilisearch_rebuilder):
    """Test the finish method when an error occurs during swap."""
    index = meilisearch_rebuilder.index
    original_name = "existing_index"
    index._name = original_name

    task = index.client.create_index(original_name)
    index.client.wait_for_task(task.task_uid)
    task = index.client.create_index(f"{original_name}_new")
    index.client.wait_for_task(task.task_uid)

    assert is_in_meilisearch(index.client, original_name)
    assert is_in_meilisearch(index.client, f"{original_name}_new")

    with patch.object(index.client, 'swap_indexes', side_effect=Exception('Swap failed')):
        with pytest.raises(MeiliSearchRebuildException, match="Error while finishing the rebuild: Swap failed"):
            meilisearch_rebuilder.finish()


def test_finish_with_swap_failure(meilisearch_rebuilder):
    """Test the finish method when swap operation fails."""
    index = meilisearch_rebuilder.index
    main_index_name = "wagtailmeili_testapp_moviepage"
    temp_index_name = f"{main_index_name}_new"
    index._name = main_index_name
    index.name = temp_index_name

    task = index.client.create_index(main_index_name)
    index.client.wait_for_task(task.task_uid)
    task = index.client.create_index(temp_index_name)
    index.client.wait_for_task(task.task_uid)

    assert is_in_meilisearch(index.client, main_index_name)
    assert is_in_meilisearch(index.client, temp_index_name)

    with patch('wagtailmeili.rebuilder.check_for_task_successful_completion') as mock_check:
        mock_check.return_value = False  # Swap operation fails

        with pytest.raises(MeiliSearchRebuildException) as excinfo:
            meilisearch_rebuilder.finish()

        assert "Failed to swap indexes" in str(excinfo.value)

    index.client.delete_index(main_index_name)
    index.client.delete_index(temp_index_name)


def test_finish_with_deletion_warning(meilisearch_rebuilder):
    """Test the finish method when temporary index deletion fails but swap succeeds."""
    index = meilisearch_rebuilder.index
    main_index_name = "test_finish_warning"
    temp_index_name = f"{main_index_name}_new"
    index._name = main_index_name
    index.name = temp_index_name

    task = index.client.create_index(main_index_name)
    index.client.wait_for_task(task.task_uid)
    task = index.client.create_index(temp_index_name)
    index.client.wait_for_task(task.task_uid)

    with patch('wagtailmeili.rebuilder.check_for_task_successful_completion') as mock_check:
        mock_check.side_effect = [True, False]  # First call (swap) succeeds, second call (delete) fails

        with patch('wagtailmeili.rebuilder.logger') as mock_logger:
            task = meilisearch_rebuilder.finish()
            mock_logger.warning.assert_called_once_with(
                    f"Failed to delete temporary index {temp_index_name}"
            )

    index.client.delete_index(main_index_name)
    if is_in_meilisearch(index.client, temp_index_name):
        index.client.delete_index(temp_index_name)


def test_reset_index_delete_failure(meilisearch_rebuilder):
    """Test reset_index when document deletion fails."""
    index = meilisearch_rebuilder.index
    test_index_name = "test_reset_failure"

    task = index.client.create_index(test_index_name)
    index.client.wait_for_task(task.task_uid)

    with patch('wagtailmeili.rebuilder.check_for_task_successful_completion') as mock_check:
        mock_check.return_value = False

        with pytest.raises(MeiliSearchRebuildException) as excinfo:
            MeilisearchRebuilder.reset_index(index)

        assert "Failed to delete documents from index" in str(excinfo.value)

    index.client.delete_index(test_index_name)


def test_delete_all_indexes_failure(meilisearch_rebuilder):
    """Test delete_all_indexes when index deletion fails."""
    index = meilisearch_rebuilder.index

    mock_index = Mock()
    mock_index.uid = "test_index"
    mock_indexes = {'results': [mock_index]}

    with patch.object(index.client, 'get_indexes', return_value=mock_indexes):
        with patch('wagtailmeili.rebuilder.check_for_task_successful_completion') as mock_check:
            mock_check.return_value = False

            with pytest.raises(MeiliSearchRebuildException) as excinfo:
                MeilisearchRebuilder.delete_all_indexes(index)

            error_msg = "Failed to delete index test_index"
            assert error_msg in str(excinfo.value)