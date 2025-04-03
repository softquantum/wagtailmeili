"""Custom managers for MeiliSearch."""

from django.db.models import Manager, QuerySet
from wagtail.models import PageManager, PageQuerySet


class MeiliSearchQuerySetMixin:
    """Mixin for MeiliSearchQuerySet.

    The method get_search_backend()
    defaults to the 'meilisearch' search backend configured for Wagtail
    """

    def search(self, query, fields=None, operator=None, order_by_relevance=True, opt_params=None):
        from wagtail.search.backends import get_search_backend

        search_backend = get_search_backend(backend="meilisearch")
        return search_backend.search(
            query,
            self,
            fields=fields,
            operator=operator,
            order_by_relevance=order_by_relevance,
            opt_params=opt_params,
        )


class MeiliSearchModelQuerySet(MeiliSearchQuerySetMixin, QuerySet):
    """QuerySet for MeiliSearchModelManager."""

    pass


class MeiliSearchPageQuerySet(MeiliSearchQuerySetMixin, PageQuerySet):
    """QuerySet for MeiliSearchPageManager."""

    pass


MeilisearchModelManager = Manager.from_queryset(MeiliSearchModelQuerySet)


MeilisearchPageManager = PageManager.from_queryset(MeiliSearchPageQuerySet)
