# accounts/tests/fixtures.py
"""
Reusable test fixtures for the accounts project.
Kept in its own module to keep each test file small and focused.
"""
from typing import Any, Dict

from .context import BaseAccountTest


def sample_profile_data(**overrides: Any) -> Dict[str, Any]:
    """Return a sample profile dict that can be reused in multiple tests."""
    defaults = {
        "first_name": "Sample",
        "last_name": "User",
        "email": "sample@example.test",
        "phone": "+237123456789",
        "city": "Douala",
        "neighborhood": "Akwa",
    }
    defaults.update(overrides)
    return defaults
