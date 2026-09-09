# accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        """
        Charge les signaux quand l'application est prête.
        """
        import accounts.signals  # noqa: F401
