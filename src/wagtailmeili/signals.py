"""Signal handlers for real-time index cleanup."""

import logging
from wagtail.signals import page_unpublished
from wagtail.search.backends import get_search_backend

logger = logging.getLogger(__name__)


def handle_page_unpublish(sender, instance, **kwargs):
    """Handle page unpublishing by removing from search index.

    When a page is unpublished, Wagtail fires a post_save signal (not post_delete).
    The backend's add() method is called via Wagtail's signal handlers.
    Since prepare_documents() returns empty list for unpublished pages (live=False),
    the page won't be re-indexed, but it remains in the index from when it was live.
    This handler explicitly removes it from the index.

     Wagtail's unpublish action modifies page.live to False and calls page.save(),
     which triggers Django's post_save signal (see wagtail/actions/unpublish_page.py:44-46).
     Wagtail's search backends listen to post_save signals and call insert_or_update_object()
     (see wagtail/search/signal_handlers.py:6-27).

     Signal firing order when unpublishing:
     1. page.live = False
     2. page.save() → Django's post_save signal fires
     3. Wagtail's post_save_signal_handler calls backend.add(instance)
     4. page_unpublished signal fires (Wagtail-specific, after post_save)

     Since prepare_documents() returns an empty list for live=False pages,
     the unpublished page won't be re-indexed via the post_save handler.
     However, the document remains in MeiliSearch from when it was live.

     This handler listens to Wagtail's page_unpublished signal (which fires after
     post_save) to explicitly delete the document from the search index, ensuring
     unpublished pages don't appear in search results.

     Having only live pages in the indexes is a design decision
     to keep the search index lean and focused on live content.

    """
    try:
        backend = get_search_backend("meilisearch")
        index = backend.get_index_for_model(type(instance))

        if index is None:
            return

        pk = getattr(instance, "pk", None)
        if pk is not None:
            index.delete_item(pk)
            logger.info(f"Removed unpublished page {instance} (pk={pk}) from search index")

    except Exception as e:
        logger.error(
            f"Failed to remove unpublished page {instance} from search index: {e}"
        )


def connect_signals():
    """Connect signal handlers for page unpublish events."""
    page_unpublished.connect(handle_page_unpublish)
