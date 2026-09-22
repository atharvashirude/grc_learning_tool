"""Global pytest fixtures and test configuration."""

import pytest


@pytest.fixture
def sample_fixture() -> str:
    """Provide a baseline fixture for test infrastructure validation."""
    return "grc_learning_tool_fixture"
