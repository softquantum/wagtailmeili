import logging
from warnings import warn

from wagtail.search.backends.base import BaseSearchQueryCompiler
from wagtail.search.query import And, Fuzzy, MatchAll, Or, Phrase, PlainText

logger = logging.getLogger(__name__)


class MeilisearchQueryCompiler(BaseSearchQueryCompiler):
    """Class for compiling a search query to MeiliSearch."""

    DEFAULT_OPERATOR = "and"
    MEILISEARCH_VALID_OPT_PARAMS = [
        "attributesToCrop",
        "attributesToHighlight",
        "attributesToRetrieve",
        "attributesToSearchOn",
        "cropLength",
        "cropMarker",
        "facets",
        "filter",
        "highlightPostTag",
        "highlightPreTag",
        "hitsPerPage",
        "limit",
        "matchingStrategy",
        "offset",
        "page",
        "showMatchesPosition",
        "showRankingScore",
        "sort",
    ]

    def __init__(self, queryset, query, fields=None, operator=None, order_by_relevance=True):
        super().__init__(queryset, query, fields, operator, order_by_relevance)
        self.queryset = queryset
        if query is None:
            warn("Querying `None` is deprecated, use `MATCH_ALL` instead.", DeprecationWarning, stacklevel=2)
            query = MatchAll()
        self.query = query
        self.fields = fields
        self.order_by_relevance = order_by_relevance
        self.opt_params = dict()

    def _process_lookup(self, field, lookup, value) -> str:
        """Process a single lookup operation.

        This method is called for each field in the query and should convert each
        Django-style field lookup into a format understood by Meilisearch.
        Meilisearch doesn't support some of the more complex lookups available in Django's ORM,
        like relational field lookups (__ syntax).  For more complex queries, consider
        preprocessing the query in Django before sending it to Meilisearch.
        """
        if lookup == "exact":
            return f'{field}:"{value}"'
        elif lookup == "iexact":
            return f'{field}:"{value.lower()}"'
        elif lookup in ["contains", "icontains"]:
            return f"{field}:{value}"
        elif lookup == "in":
            if isinstance(value, (list, tuple)):
                return " OR ".join([f"{field}:{v}" for v in value])
            else:
                return f"{field}:{value}"
        elif lookup == "gt":
            return f"{field} > {value}"
        elif lookup == "gte":
            return f"{field} >= {value}"
        elif lookup == "lt":
            return f"{field} < {value}"
        elif lookup == "lte":
            return f"{field} <= {value}"
        elif lookup == "range":
            start, end = value
            return f"{field} {start} TO {end}"
        elif lookup == "exclude":
            return f"NOT {field}:{value}"
        elif lookup == "isnull":
            return f"{field} = NULL" if value else f"{field} != NULL"
        elif lookup == "startswith":
            return f"{field}:{value}*"
        elif lookup == "endswith":
            return f"{field}:*{value}"
        else:
            logger.warning(f"Unhandled lookup: {lookup} for field {field}")
            return ""

    def _connect_filters(self, filters, connector, negated) -> str:
        """Connect multiple filters using the specified connector.

        Combines individual lookups into a single query string, using logical
        connectors like AND/OR.  This is where you handle the logic of how
        different filters are combined in Meilisearch.  Negation might be
        tricky and not directly supported.
        """
        query_string = f" {connector} ".join(filters)
        if negated:
            return f"NOT ({query_string})"
        return query_string

    def _compile_query(self, query, fields):
        if isinstance(query, MatchAll):
            return ""
        elif isinstance(query, And):
            return " ".join(self._compile_query(child_query, [fields]) for child_query in query.subqueries)
        elif isinstance(query, Or):
            return " ".join(self._compile_query(child_query, [fields]) for child_query in query.subqueries)
        elif isinstance(query, PlainText):
            return query.query_string
        elif isinstance(query, Fuzzy):
            return query.query_string
        elif isinstance(query, Phrase):
            return f'"{query.query_string}"'  # double quotes are important here
        else:  # TODO: Boost, Not
            return query  # if not using one of the above

    def get_query(self):
        """Compile the query to send to MeiliSearch.

        Wagtail is receiving a query string on the form Model.search(query_string)
        Since the backend does not control what the developers can do, the formats could be
        on different forms: str, Phrase, PlainText, etc.
        This method should return a query string that can be used in Meilisearch.

        """
        query = self._compile_query(self.query, self.fields)
        return query

    def set_opt_params(self, params):
        """Set a sanitized optional parameters for the MeiliSearch query."""
        # TODO: review the flow with opt_params
        opt_params = {param: params[param] for param in self.MEILISEARCH_VALID_OPT_PARAMS if param in params}
        self.opt_params.update(opt_params)


class MeilisearchAutocompleteQueryCompiler(MeilisearchQueryCompiler):
    """Class for compiling an autocomplete query to MeiliSearch.

    Sets prefix: True by default for autocomplete functionality.
    Uses attributesToSearchOn to limit the search to autocomplete fields.
    Simplified get_query() method since autocomplete only needs to handle basic text queries.

    """

    def __init__(self, queryset, query, fields=None, operator=None, order_by_relevance=True):
        super().__init__(queryset, query, fields, operator, order_by_relevance)

        if self.fields:
            self.searchable_fields = []
            autocomplete_fields = {
                f.field_name: f
                for f in self.queryset.model.get_autocomplete_search_fields()
            }

            for field_name in self.fields:
                if field_name in autocomplete_fields:
                    self.searchable_fields.append(field_name)
        else:
            self.searchable_fields = [
                f.field_name
                for f in self.queryset.model.get_autocomplete_search_fields()
            ]

        self.opt_params.update({
            "attributesToSearchOn": self.searchable_fields,
        })

    def get_query(self):
        if isinstance(self.query, MatchAll):
            return ""
        elif isinstance(self.query, PlainText):
            return self.query.query_string
        elif isinstance(self.query, str):
            return self.query
        else:
            raise NotImplementedError(
                f"`{self.query.__class__.__name__}` is not supported for autocomplete queries."
            )
