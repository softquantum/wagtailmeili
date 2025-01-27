from django.apps import AppConfig


class WagtailLocalizeTestAppConfig(AppConfig):
    label = "wagtailmeili_testapp"
    name = "wagtailmeili.testapp"
    verbose_name = "Wagtail Meilisearch Test app"
    default_auto_field = "django.db.models.BigAutoField"
