import time

import pytest

from wagtailmeili.testapp.models import MoviePageWithManager


@pytest.mark.django_db
def test_meilisearch_model_manager_search(meilisearch_index, load_movies_data):
    search_results = MoviePageWithManager.objects.search("", opt_params={"hitsPerPage": 5}).get()
    assert search_results is not None
    assert len(search_results["hits"]) == 5


@pytest.mark.django_db
def test_meilisearch_model_manager_search_with_updated_opt_param(meilisearch_index, load_movies_data):
    search_results = MoviePageWithManager.objects.search("", opt_params={"limit": 1}).get()
    assert len(search_results["hits"]) == 1
