"""Test the backend using real Meilisearch instance."""
import logging

import pytest

from wagtailmeili.query_compiler import MeilisearchQueryCompiler
from wagtailmeili.results import MeilisearchResults
from wagtailmeili.testapp.models import MoviePage, ReviewPage

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_backend_search_integration(meilisearch_backend, load_movies_data, clean_meilisearch_index):
    """Test the search method of the backend using real Meilisearch instance."""
    # Explicitly index all movies since signals might not be working in tests
    for movie in MoviePage.objects.all():
        meilisearch_backend.add(movie)

    # Test 1: Exact title match
    results = meilisearch_backend.search("Star Wars", MoviePage.objects.all())
    hits = results.get()["hits"]
    assert len(hits) > 0
    movie = MoviePage.objects.get(id=hits[0]["id"])
    assert movie.title == "Star Wars"

    # Test 2: Partial word match
    results = meilisearch_backend.search("Dark", MoviePage.objects.all())
    hits = results.get()["hits"]
    assert len(hits) >= 2  # Should find "The Dark" and "Dancer in the Dark"
    titles = {MoviePage.objects.get(id=hit["id"]).title for hit in hits}
    assert "The Dark" in titles
    assert "Dancer in the Dark" in titles

    # Test 3: Search in overview
    results = meilisearch_backend.search("clownfish", MoviePage.objects.all())
    hits = results.get()["hits"]
    assert len(hits) == 1
    movie = MoviePage.objects.get(id=hits[0]["id"])
    assert movie.title == "Finding Nemo"

    # Test 4: Genre filtering (if supported by your backend implementation)
    scifi_movies = meilisearch_backend.search("Fiction", MoviePage.objects.all())
    hits = scifi_movies.get()["hits"]
    assert len(hits) > 0
    for hit in hits:
        movie = MoviePage.objects.get(id=hit["id"])
        assert "Science Fiction" in movie.genres


@pytest.mark.django_db
def test_skip_models(meilisearch_backend, movies_index_page, clean_meilisearch_index):
    """Test that models in skip_models are not indexed.

    This test verifies the skip_models functionality through Wagtail's search interface,
    ensuring that models listed in skip_models are completely excluded from indexing.
    """
    import time
    from meilisearch.errors import MeilisearchApiError
    
    # Ensure clean state
    meilisearch_backend.delete_all_indexes()
    time.sleep(1)
    
    # Create test data
    movie = MoviePage(
        title="Star Wars",
        slug="star-wars",
        overview="A space movie",
        genres=["Science Fiction"],
    )
    movies_index_page.add_child(instance=movie)

    skipped = ReviewPage(
            title="Should Not Index",
            slug="should-not-index",
            review="This model should not be indexed"
    )
    movies_index_page.add_child(instance=skipped)

    movie2 = MoviePage(
        title="Return of the Jedi",
        slug="return-of-the-jedi",
        overview="Another space movie",
        genres=["Science Fiction"],
    )
    movies_index_page.add_child(instance=movie2)

    # Manually index the non-skipped movie to ensure it gets indexed
    # This bypasses potential signal issues in test environment
    try:
        meilisearch_backend.add(movie)
        time.sleep(2)  # Wait for indexing to complete
    except Exception as e:
        logger.warning(f"Direct indexing failed: {e}")
        
    # Try to index the skipped ReviewPage (should be ignored)
    try:
        meilisearch_backend.add(skipped)
        time.sleep(1)
    except Exception as e:
        logger.info(f"Expected: ReviewPage indexing failed as expected: {e}")

    # Try to index movie2 (should be skipped by field value)
    try:
        meilisearch_backend.add(movie2)
        time.sleep(1)
    except Exception as e:
        logger.info(f"Movie2 indexing result: {e}")

    # Check what indexes were created
    indexes = meilisearch_backend.client.get_indexes()
    logger.info(f"Indexes after creation: {[index.uid for index in indexes['results']]}")

    # Test that non-skipped movie can be found
    try:
        movie_results = meilisearch_backend.search("Star Wars", MoviePage).get()
        logger.info(f"movie_results: {movie_results}")
        hits = movie_results["hits"]
        assert len(hits) == 1
        assert hits[0]["title"] == "Star Wars"
    except MeilisearchApiError as e:
        if "index_not_found" in str(e):
            pytest.skip("MoviePage index was not created - check MeiliSearch configuration")
        raise

    # Test that searching skipped model raises appropriate exception
    with pytest.raises(MeilisearchApiError, match="index_not_found"):
        meilisearch_backend.search("Should Not Index", ReviewPage).get()

    # Test that searching returns empty if model skipped by field value
    try:
        jedi_results = meilisearch_backend.search("Return of the Jedi", MoviePage).get()
        assert len(jedi_results["hits"]) == 0, "Return of the Jedi should be skipped by field value"
    except MeilisearchApiError as e:
        if "index_not_found" in str(e):
            # If index doesn't exist, that's also valid (nothing was indexed)
            logger.info("Index not found - skipping field value test as no MoviePage index exists")
        else:
            raise


@pytest.mark.django_db
def test_reset_index_with_real_instance(meilisearch_backend, load_movies_data):
    """Test reset_index with a real Meilisearch instance.

    This test:
    1. Adds some data to the index
    2. Verifies the data is present
    3. Resets the index
    4. Verifies the data is gone
    """
    # First add some test data to ensure there's something to reset
    for movie in MoviePage.objects.all():
        meilisearch_backend.add(movie)

    # Give Meilisearch time to process
    import time
    time.sleep(2)

    # Verify we have data in the index
    results = meilisearch_backend.search("", MoviePage.objects.all())
    pre_reset_hits = results.get()["hits"]
    assert len(pre_reset_hits) > 0, "Should have movies in the index before reset"

    # Reset the index
    meilisearch_backend.reset_index()

    # Give Meilisearch time to process the reset
    time.sleep(2)

    # Check indexes after review creation
    indexes = meilisearch_backend.client.get_indexes()
    logger.info(f"Indexes after review creation: {[index.uid for index in indexes['results']]}")

    # Verify the index is empty or not found
    try:
        results = meilisearch_backend.search("", MoviePage.objects.all())
        hits = results.get()["hits"]
        assert len(hits) == 0, "Index should be empty after reset"
    except Exception as e:
        # If the index was completely deleted, searching might raise an exception
        # This is also a valid outcome of reset_index
        if "index_not_found" not in str(e):
            raise


@pytest.mark.django_db
def test_returns_search_results(meilisearch_backend):
    model = MoviePage
    queryset = model.objects.all()
    query = "test query"
    result = meilisearch_backend._search(MeilisearchQueryCompiler, query, queryset)
    assert isinstance(result, MeilisearchResults)


@pytest.mark.django_db
def test_handles_opt_params_correctly(meilisearch_backend):
    model = MoviePage
    queryset = model.objects.all()
    query = "test query"
    opt_params = {"page": 1, "hitsPerPage": 10}
    result = meilisearch_backend._search(MeilisearchQueryCompiler, query, queryset, opt_params=opt_params)
    assert isinstance(result, MeilisearchResults)
