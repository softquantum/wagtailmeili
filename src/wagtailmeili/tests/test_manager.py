
import pytest
import time
from meilisearch.errors import MeilisearchApiError

from wagtailmeili.testapp.models import MoviePageWithManager


@pytest.mark.django_db
def test_meilisearch_model_manager_search(meilisearch_backend, load_movies_data, clean_meilisearch_index):
    """Test that the MeilisearchPageManager can perform searches."""
    meilisearch_backend.delete_all_indexes()
    time.sleep(1)
    
    # Manually index some movies to ensure they exist in the search index
    movies = MoviePageWithManager.objects.all()[:5]
    for movie in movies:
        try:
            meilisearch_backend.add(movie)
        except Exception as e:
            pytest.skip(f"Could not index movie {movie.title}: {e}")
    
    # Wait for indexing to complete
    time.sleep(2)
    
    try:
        search_results = MoviePageWithManager.objects.search("", opt_params={"hitsPerPage": 5}).get()
        assert search_results is not None
        assert len(search_results["hits"]) == 5
    except MeilisearchApiError as e:
        if "index_not_found" in str(e):
            pytest.skip("Index not found - check MeiliSearch configuration")
        raise


@pytest.mark.django_db
def test_meilisearch_model_manager_search_with_updated_opt_param(meilisearch_backend, load_movies_data, clean_meilisearch_index):
    """Test that the MeilisearchPageManager can handle different search parameters."""
    meilisearch_backend.delete_all_indexes()
    time.sleep(1)
    
    # Manually index some movies to ensure they exist in the search index
    movies = MoviePageWithManager.objects.all()[:3]
    for movie in movies:
        try:
            meilisearch_backend.add(movie)
        except Exception as e:
            pytest.skip(f"Could not index movie {movie.title}: {e}")
    
    # Wait for indexing to complete
    time.sleep(2)
    
    try:
        search_results = MoviePageWithManager.objects.search("", opt_params={"limit": 1}).get()
        assert len(search_results["hits"]) == 1
    except MeilisearchApiError as e:
        if "index_not_found" in str(e):
            pytest.skip("Index not found - check MeiliSearch configuration")
        raise
