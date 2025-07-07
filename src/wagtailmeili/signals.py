"""Signal handlers for real-time index cleanup."""

import logging
from django.db.models.signals import post_delete
from wagtail.signals import page_unpublished
from wagtail.search.backends import get_search_backend

logger = logging.getLogger(__name__)


def handle_item_deletion(sender, instance, **kwargs):
    """Handle real-time deletion from search index."""
    try:
        # Skip if this is not a model we care about
        if not hasattr(sender, "_meta"):
            return

        # Skip Wagtail's internal models
        if sender._meta.app_label == "wagtailsearch":
            return

        backend = get_search_backend("meilisearch")
        index = backend.get_index_for_model(sender)

        if index is None:
            # Model is not indexed or backend doesn't support this model
            return

        # Store pk before deletion since instance may not have pk after delete signal
        pk = kwargs.get("pk") or getattr(instance, "pk", None)

        if pk is not None:
            index.delete_item(pk)
            logger.info(f"Deleted {sender.__name__} {pk} from search index")

    except Exception as e:
        logger.error(
            f"Failed to delete {sender.__name__} {getattr(instance, 'pk', 'unknown')} from search index: {e}"
        )


def handle_page_unpublish(sender, instance, **kwargs):
    """Handle page unpublishing."""
    handle_item_deletion(sender, instance, **kwargs)


def connect_signals():
    """Connect all signal handlers."""
    # Connect delete signals for all models
    post_delete.connect(handle_item_deletion)

    # Connect page unpublish signal
    page_unpublished.connect(handle_page_unpublish)
