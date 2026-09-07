# accounts/tests/setup.py
"""
Test setup helpers for the accounts project.
Kept in one file to avoid duplicating boilerplate across many small test files.
"""
from django.conf import settings


def configure_test_settings():
    """Ensure Django settings are configured for tests if not already present."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.messages",
                "django.contrib.sessions",
                "django.contrib.staticfiles",
                "accounts",
                "administration",
                "catalog",
                "garages",
                "notifications",
                "orders",
                "payments",
                "reviews",
                "support",
                "vehicles",
                "search",
                "core",
            ],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.debug",
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                },
            ],
            ROOT_URLCONF="autolink.urls",
            SECRET_KEY="test-secret-key-not-for-production",
            USE_TZ=True,
        )
