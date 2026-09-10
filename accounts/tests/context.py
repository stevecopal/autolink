# accounts/tests/context.py
"""
Shared test fixtures and context builders for project-level helpers.
Avoids a single enormous test file by centralizing common helpers.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseAccountTest(TestCase):
    """Base class with reusable account/user helpers."""

    def create_user(self, **kwargs):
        defaults = {
            "username": "testuser",
            "email": "test@example.test",
            "first_name": "Test",
            "last_name": "User",
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)

    def create_admin_user(self):
        return self.create_user(
            username="admin",
            role="ADMIN",
            email="admin@example.test",
        )
