import pytest

from wagtailmeili import VERSION
from wagtailmeili.version import get_version, get_complete_version


def test_version_mapping_for_pre_release():
    """Test that version mapping works correctly for pre-release versions."""
    test_cases = [
        ((1, 0, 0, "alpha", 1), "1.0a1"),      # Z is 0, so it's omitted
        ((2, 1, 0, "beta", 2), "2.1b2"),       # Z is 0, so it's omitted
        ((1, 5, 2, "rc", 3), "1.5.2rc3"),      # Z is 2, so it's included
        ((2, 0, 1, "dev", 1), "2.0.1.dev1"),   # Z is 1, so it's included
        ((2, 1, 0, "dev", 1), "2.1.dev1"),     # Z is 0, so it's omitted
    ]

    for version_tuple, expected in test_cases:
        result = get_version(version_tuple)
        assert result == expected, f"For version {version_tuple}, expected {expected}, but got {result}"


def test_version_validation_length():
    """Test that version validation catches incorrect tuple lengths."""
    invalid_versions = [
        (1, 0, 0, "final"),  # Too short
        (1, 0, 0, "final", 0, "extra"),  # Too long
    ]

    for version in invalid_versions:
        with pytest.raises(ValueError) as exc_info:
            get_complete_version(version)
        assert str(exc_info.value) == "wagtailmeili version number must be a 5-tuple"


def test_version_validation_status():
    """Test that version validation catches invalid status values."""
    invalid_versions = [
        (1, 0, 0, "gamma", 0),  # Invalid status
        (1, 0, 0, "final2", 0),  # Invalid status
        (1, 0, 0, "", 0),  # Empty status
    ]

    for version in invalid_versions:
        with pytest.raises(ValueError) as exc_info:
            get_complete_version(version)
        assert str(exc_info.value) == (
            "wagtailmeili version status must be one of: dev, alpha, beta, rc, or final"
        )


def test_version_validation_valid_status():
    """Test that version validation accepts all valid status values."""
    valid_statuses = ["dev", "alpha", "beta", "rc", "final"]

    for status in valid_statuses:
        version = (1, 0, 0, status, 0)
        assert get_complete_version(version) == version


def test_get_complete_version_without_argument():
    """Test that get_complete_version works when called without arguments."""
    result = get_complete_version()
    assert result == VERSION
    assert len(result) == 5
    assert result[3] in ("dev", "alpha", "beta", "rc", "final")
    assert isinstance(result[4], int)
