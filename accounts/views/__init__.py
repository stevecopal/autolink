# accounts/views/__init__.py
"""
Accounts application views — split into submodules for maintainability.
"""
from .account_views import (
    RegisterView,
    LoginView,
    logout_view,
    profile_view,
    profile_edit_view,
    client_dashboard_view,
    notification_list_view,
    notification_mark_read_view,
    notification_mark_all_read_view,
)

__all__ = [
    "RegisterView",
    "LoginView",
    "logout_view",
    "profile_view",
    "profile_edit_view",
    "client_dashboard_view",
    "notification_list_view",
    "notification_mark_read_view",
    "notification_mark_all_read_view",
]
