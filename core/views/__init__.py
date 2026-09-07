# core/views/__init__.py
"""
Core application views — split into submodules for maintainability.
"""
from .home import home_view
from .search_form import search_view
from .about import about_view
from .contact import contact_view
from .policy import policy_view
from .api import neighborhoods_api

__all__ = ["home_view", "search_view", "about_view", "contact_view", "policy_view", "neighborhoods_api"]
