"""Tests for cleanup_search_index management command."""
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from django.core.management import call_command

from wagtailmeili.testapp.models import MoviePage


@pytest.mark.django_db
def test_cleanup_command_dry_run():
    """Test that cleanup command works in dry-run mode."""
    with patch('wagtailmeili.management.commands.cleanup_search_index.get_search_backend') as mock_backend:
        with patch('wagtailmeili.management.commands.cleanup_search_index.get_indexed_models') as mock_models:
            mock_index = MagicMock()
            mock_docs = MagicMock()
            mock_docs.results = [{"id": "1"}, {"id": "2"}, {"id": "999"}]  # 999 is stale
            mock_index.index.get_documents.return_value = mock_docs
            
            mock_search_backend = MagicMock()
            mock_search_backend.get_index_for_model.return_value = mock_index
            mock_backend.return_value = mock_search_backend
            
            mock_models.return_value = [MoviePage]
            
            with patch.object(MoviePage.objects, 'filter') as mock_filter:
                mock_values_list = MagicMock()
                mock_values_list.return_value = [1, 2]  # Only these are live
                mock_filter.return_value.values_list = mock_values_list
                
                out = StringIO()
                
                call_command('cleanup_search_index', '--dry-run', stdout=out)
                
                output = out.getvalue()
                assert "Would delete 1 stale documents" in output
                assert "Dry run complete" in output
                
                mock_index.bulk_delete_items.assert_not_called()


@pytest.mark.django_db 
def test_cleanup_command_actual_run():
    """Test that cleanup command actually deletes stale documents."""
    with patch('wagtailmeili.management.commands.cleanup_search_index.get_search_backend') as mock_backend:
        with patch('wagtailmeili.management.commands.cleanup_search_index.get_indexed_models') as mock_models:
            mock_index = MagicMock()
            mock_docs = MagicMock()
            mock_docs.results = [{"id": "1"}, {"id": "2"}, {"id": "999"}]  # 999 is stale
            mock_index.index.get_documents.return_value = mock_docs
            
            mock_search_backend = MagicMock()
            mock_search_backend.get_index_for_model.return_value = mock_index
            mock_backend.return_value = mock_search_backend
            
            mock_models.return_value = [MoviePage]
            
            with patch.object(MoviePage.objects, 'filter') as mock_filter:
                mock_values_list = MagicMock()
                mock_values_list.return_value = [1, 2]  # Only these are live
                mock_filter.return_value.values_list = mock_values_list
                
                out = StringIO()
                
                call_command('cleanup_search_index', stdout=out)
                
                output = out.getvalue()
                assert "Deleted 1 stale documents" in output
                assert "Successfully cleaned 1 stale documents" in output
                
                mock_index.bulk_delete_items.assert_called_once_with(["999"])


@pytest.mark.django_db
def test_cleanup_command_specific_model():
    """Test that cleanup command can target a specific model."""
    with patch('wagtailmeili.management.commands.cleanup_search_index.get_search_backend') as mock_backend:
        mock_index = MagicMock()
        mock_docs = MagicMock()
        mock_docs.results = [{"id": "1"}]
        mock_index.index.get_documents.return_value = mock_docs
        
        mock_search_backend = MagicMock()
        mock_search_backend.get_index_for_model.return_value = mock_index
        mock_backend.return_value = mock_search_backend
        
        with patch.object(MoviePage.objects, 'filter') as mock_filter:
            mock_values_list = MagicMock()
            mock_values_list.return_value = [1]
            mock_filter.return_value.values_list = mock_values_list
            
            out = StringIO()
            
            call_command('cleanup_search_index', '--model', 'wagtailmeili_testapp.MoviePage', stdout=out)
            
            mock_search_backend.get_index_for_model.assert_called_once_with(MoviePage)


@pytest.mark.django_db
def test_cleanup_command_no_stale_documents():
    """Test that cleanup command handles case with no stale documents."""
    with patch('wagtailmeili.management.commands.cleanup_search_index.get_search_backend') as mock_backend:
        with patch('wagtailmeili.management.commands.cleanup_search_index.get_indexed_models') as mock_models:
            mock_index = MagicMock()
            mock_docs = MagicMock()
            mock_docs.results = [{"id": "1"}, {"id": "2"}]  # No stale docs
            mock_index.index.get_documents.return_value = mock_docs
            
            mock_search_backend = MagicMock()
            mock_search_backend.get_index_for_model.return_value = mock_index
            mock_backend.return_value = mock_search_backend
            
            mock_models.return_value = [MoviePage]
            
            with patch.object(MoviePage.objects, 'filter') as mock_filter:
                mock_values_list = MagicMock()
                mock_values_list.return_value = [1, 2]  # All docs are live
                mock_filter.return_value.values_list = mock_values_list
                
                out = StringIO()
                
                call_command('cleanup_search_index', '--verbosity', '1', stdout=out)
                
                output = out.getvalue()
                assert "No stale documents found" in output
                assert "Successfully cleaned 0 stale documents" in output
                
                mock_index.bulk_delete_items.assert_not_called()
                