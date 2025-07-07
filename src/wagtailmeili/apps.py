from django.apps import AppConfig


class WagtailMeiliConfig(AppConfig):
    """App configuration for Wagtail Meilisearch."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "wagtailmeili"
    
    def ready(self):
        """Connect signal handlers when the app is ready."""
        from .signals import connect_signals
        connect_signals()
