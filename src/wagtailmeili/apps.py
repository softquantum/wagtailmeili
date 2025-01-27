from django.apps import AppConfig


class WagtailMeiliConfig(AppConfig):
    """App configuration for Wagtail Meilisearch."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "wagtailmeili"
