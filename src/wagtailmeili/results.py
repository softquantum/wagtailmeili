import logging
from collections import OrderedDict

from wagtail.search.backends.base import BaseSearchResults, EmptySearchResults, FilterFieldError

logger = logging.getLogger("search")

# `hitsPerPage` forces meilisearch to respond with `totalHits` instead of `estimatedTotalHits`, use with caution
# TODO: Verify the "facets": [],
DEFAULT_OPT_PARAMS = {
    "showMatchesPosition": True,
    "matchingStrategy": "last",
    "limit": 10,
}


class MeilisearchResults(BaseSearchResults):
    """Class for search results from MeiliSearch."""

    supports_facet = True

    def __init__(self, backend, query_compiler, prefetch_related=None):
        super().__init__(backend, query_compiler, prefetch_related)
        self.backend = backend
        self.query_compiler = query_compiler  # MeilisearchQueryCompiler or MeilisearchAutocompleteQueryCompiler
        self.prefetch_related = prefetch_related
        self.start = 0
        self.stop = None
        self._results_cache = None
        self._count_cache = None
        self._score_field = None
        self.model = self.query_compiler.queryset.model
        self.index = self.backend.get_index_for_model(self.model)
        self.filterable_attributes = self.backend.client.index(self.index.name).get_filterable_attributes()
        self.opt_params = DEFAULT_OPT_PARAMS.copy()
        if self.query_compiler.opt_params:
            self.opt_params.update(self.query_compiler.opt_params)

    def get_results_count(self, results) -> int:
        """Get the number of hits from results."""
        if "totalHits" in results:
            return results["totalHits"]
        elif "estimatedTotalHits" in results:
            return results["estimatedTotalHits"]
        else:
            return len(results)

    def _get_model_pks(self, hits):
        """Get the primary keys from hits."""
        return [int(hit["id"]) for hit in hits]  # TODO: Assuming 'id' is the primary key in the hits

    def _do_search(self):
        """Implement the search on Meilisearch.

        Args:
        ----
            query_string (str): the query string to search for.
            model (Model): the model to search in.
            index (str): the index to search in.
            opt_params (dict):  default values {
                    "offset": 0,
                    "limit": 20,
                    "hitsPerPage": 1,
                    "page": 1,
                    "filter": null,  # string
                    "facets": null,  # array of strings
                    "attributesToRetrieve": ["*"],  # array of strings
                    "attributesToCrop": null,  # array of strings
                    "cropLength": 10,
                    "cropMarker": "..."
                    "attributesToHighlight": null,  # array of strings
                    "highlightPreTag": "<em>",
                    "highlightPostTag": "</em>",
                    "showMatchesPosition": false,
                    "sort": null,  # array of strings,
                    "matchingStrategy": "last",
                    "showRankingScore": false,
                    "attributesToSearchOn": ["*"],  # array of strings
                }
        """
        query_string = self.query_compiler.get_query()

        # Execute the search
        raw_search_results = self.backend.client.index(self.index.name).search(
            query=query_string, opt_params=self.opt_params
        )

        # Process the hits into Django model instances
        raw_search_results["pks"] = list(self._get_model_pks(raw_search_results["hits"]))
        raw_search_results["model"] = self.model._meta.label  # noqa: private attribute
        self._results_cache = raw_search_results
        self._count_cache = self.get_results_count(raw_search_results)

        return self._results_cache

    def _do_count(self) -> int | None:
        """Implement the count on Meilisearch."""
        if self._count_cache is None:
            self._do_search()

        return self._count_cache

    def get(self):
        """Get the search results from MeilisearchResulst class instance.

        backend.search returns an instance of MeilisearchResults
        this method returns the results dictionary returned by _do_search()
        """
        return self._do_search()

    def facet(self, field_name):
        """Get the facet results from MeilisearchResults class instance.

        Wagtail supports faceted search, which is a kind of filtering based on a taxonomy field
        (such as category or page type). The .facet(field_name) method returns an OrderedDict.
        The keys are the IDs of the related objects that have been referenced by the specified field,
        and the values are the number of references found for each ID.
        The results are ordered by the number of references descending.
        """
        model = self.query_compiler.queryset.model
        query_string = self.query_compiler.query.query_string
        index = self.backend.get_index_for_model(model)

        # Get field (_get_filterable_field is defined in BaseSearchQueryCompiler)
        field = self.query_compiler._get_filterable_field(field_name)  # noqa: protected access
        if field is None:
            raise FilterFieldError(
                'Cannot facet search results with field "'
                + field_name
                + "\". Please add index.FilterField('"
                + field_name
                + "') to "
                + self.query_compiler.queryset.model.__name__
                + ".search_fields.",
                field_name=field_name,
            )

        self.opt_params.update({"facets": [field_name]})

        facet_results = self.backend.client.index(index.name).search(
            query=query_string,
            opt_params={
                "facets": [field_name],
            },
        )

        facet_distribution = facet_results.get("facetDistribution", {}).get(field_name, {})
        sorted_results = sorted(facet_distribution.items(), key=lambda x: x[1], reverse=True)

        return OrderedDict(sorted_results)


class MeilisearchEmptySearchResults(EmptySearchResults):
    """Class for empty search results from MeiliSearch."""

    def __init__(self):
        super().__init__()

    def _clone(self):
        return self.__class__()

    def _do_search(self):
        return []

    def get(self):
        return self._do_search()

    def _do_count(self):
        return 0
