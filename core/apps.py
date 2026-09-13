from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'Core'

    def ready(self):
        # Import des signaux pour enregistrement
        from core import signals  # noqa: F401
