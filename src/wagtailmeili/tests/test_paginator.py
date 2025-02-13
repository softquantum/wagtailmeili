import pytest
from wagtailmeili.paginator import MeilisearchPaginator, PageNotAnInteger, EmptyPage


@pytest.fixture
def mock_search_results():
    """Fixture providing mock search results similar to Meilisearch response."""
    return {
        "hits": [{"id": i, "title": f"Result {i}"} for i in range(1, 21)],
        "hitsPerPage": 5,
        "totalPages": 4,
        "totalHits": 20,
    }


@pytest.fixture
def paginator(mock_search_results):
    """Fixture providing a MeilisearchPaginator instance."""
    return MeilisearchPaginator(mock_search_results)


def test_paginator_initialization(mock_search_results):
    """Test that the paginator is initialized correctly with search results."""
    paginator = MeilisearchPaginator(mock_search_results)

    assert len(paginator.object_list) == 20
    assert paginator.per_page == 5
    assert paginator.num_pages == 4
    assert paginator.count == 20


def test_validate_number_valid(paginator):
    """Test that validate_number works with valid page numbers."""
    assert paginator.validate_number(1) == 1
    assert paginator.validate_number("2") == 2


def test_validate_number_invalid(paginator):
    """Test that validate_number raises appropriate exceptions for invalid input."""
    with pytest.raises(PageNotAnInteger):
        paginator.validate_number("abc")

    with pytest.raises(EmptyPage):
        paginator.validate_number(0)

    with pytest.raises(PageNotAnInteger):
        paginator.validate_number(None)


def test_page_range(paginator):
    """Test that page_range returns correct range of pages."""
    assert list(paginator.page_range) == [1, 2, 3, 4]


def test_get_page(paginator):
    """Test getting a specific page."""
    page = paginator.page(2)
    assert page.number == 2
    assert len(page.object_list) == 20  # Full result set is on each page
    assert page.has_previous()
    assert page.has_next()
    assert page.previous_page_number() == 1
    assert page.next_page_number() == 3


def test_page_start_end_index(paginator):
    """Test page start and end index calculations."""
    page = paginator.page(2)
    assert page.start_index() == 6
    assert page.end_index() == 10


def test_has_other_pages(paginator):
    """Test has_other_pages method."""
    first_page = paginator.page(1)
    middle_page = paginator.page(2)
    last_page = paginator.page(4)

    assert first_page.has_other_pages()  # Has next but no previous
    assert middle_page.has_other_pages()  # Has both next and previous
    assert last_page.has_other_pages()  # Has previous but no next


def test_get_elided_page_range(paginator):
    """Test the elided page range functionality."""
    # Test with default values
    elided_range = list(paginator.get_elided_page_range(number=2))
    assert elided_range == [1, 2, 3, 4]  # Small number of pages, no elision

    # Create a paginator with more pages to test elision
    large_results = {
        "hits": [{"id": i} for i in range(1, 51)],
        "hitsPerPage": 5,
        "totalPages": 10,
        "totalHits": 50,
    }
    large_paginator = MeilisearchPaginator(large_results)

    # Test elision with middle page selected
    elided_range = list(large_paginator.get_elided_page_range(number=5, on_each_side=2, on_ends=1))
    assert large_paginator.ELLIPSIS in elided_range
    assert 1 in elided_range  # First page
    assert 10 in elided_range  # Last page


def test_page_repr(paginator):
    """Test the string representation of a page."""
    page = paginator.page(1)
    assert repr(page) == "<Page 1 of 4>"


def test_page_sequence_behavior(paginator):
    """Test that Page class behaves like a sequence."""
    page = paginator.page(1)

    # Test length
    assert len(page) == 20

    # Test indexing
    assert page[0]["title"] == "Result 1"

    # Test slicing
    assert len(page[0:2]) == 2

    # Test iteration
    items = [item for item in page]
    assert len(items) == 20

    # Test invalid index type
    with pytest.raises(TypeError):
        page["invalid"]
