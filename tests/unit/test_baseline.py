"""Baseline unit tests to verify test suite configuration and package imports."""

import grc_tool


def test_package_version() -> None:
    """Verify package version is defined and follows semantic versioning."""
    assert grc_tool.__version__ == "0.1.0"


def test_fixture_integrity(sample_fixture: str) -> None:
    """Verify test fixtures load and pass correctly."""
    assert sample_fixture == "grc_learning_tool_fixture"
