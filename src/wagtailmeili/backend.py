import logging
from typing import Type

from django.db.models import QuerySet
from meilisearch import Client
from wagtail.search.backends.base import BaseSearchBackend, BaseSearchResults
from wagtail.search.index import class_is_indexed

from .exceptions import MeiliSearchConnectionException
from .index import MeilisearchIndex
from .query_compiler import MeilisearchAutocompleteQueryCompiler, MeilisearchQueryCompiler
from .rebuilder import MeilisearchRebuilder
from .results import MeilisearchEmptySearchResults, MeilisearchResults
from .settings import RANKING_RULES, SKIP_MODELS, SKIP_MODELS_BY_FIELD_VALUE, STOP_WORDS

logger = logging.getLogger(__name__)


class MeilisearchBackend(BaseSearchBackend):
    """Class for MeiliSearch backend."""

    query_compiler_class = MeilisearchQueryCompiler
    autocomplete_query_compiler_class = MeilisearchAutocompleteQueryCompiler
    results_class = MeilisearchResults
    rebuilder_class = MeilisearchRebuilder
    catch_indexing_errors = True
    index_class = MeilisearchIndex

    DEFAULT_SETTINGS = {
        "STOP_WORDS": STOP_WORDS,
        "RANKING_RULES": RANKING_RULES,
        "SKIP_MODELS": SKIP_MODELS,
        "SKIP_MODELS_BY_FIELD_VALUE": SKIP_MODELS_BY_FIELD_VALUE,
        "QUERY_LIMIT": 1000,
    }

    def __init__(self, params):
        super().__init__(params)
        try:
            self.client = Client(f"{params.get('HOST')}:{params.get('PORT')}", f"{params.get('MASTER_KEY')}")
        except Exception as err:
            raise MeiliSearchConnectionException(f"Error connecting to MeiliSearch: {err}") from err

        settings = {**self.DEFAULT_SETTINGS, **params}
        self.stop_words = settings["STOP_WORDS"]
        self.ranking_rules = settings["RANKING_RULES"]
        self.skip_models = self._get_skipped_models(settings["SKIP_MODELS"])
        self.skip_models_by_field_value = self._get_skipped_models_by_field_value(settings["SKIP_MODELS_BY_FIELD_VALUE"])
        self.query_limit = settings["QUERY_LIMIT"]

    def get_rebuilder(self) -> Type[MeilisearchRebuilder]:
        return self.rebuilder_class

    def get_index_for_model(self, model) -> MeilisearchIndex:
        return self.index_class(backend=self, model=model)

    def _get_skipped_models(self, skip_models):  # noqa
        """Validate and format the skip_models list.

        Args:
            skip_models: List of models to skip for backend params.

        Returns:
            list: Validated list of model identifiers in the format "app_label.model_name"

        Raises:
            ValueError: If skip_models is not a list of strings
            ValueError: If any entry doesn't match the required "app_label.model_name" format

        Examples:
            Valid settings:
                SKIP_MODELS = [
                    "wagtailmeili_testapp.ReviewPage",  # model_name as it is defined in its class
                    "myapp.mymodel",  # lowercase is also accepted
                ]

        """
        if not skip_models:
            return []

        validated_models = []
        for model in skip_models:
            if not isinstance(model, str):
                raise ValueError(
                        f"SKIP_MODELS entries must be strings, got {type(model).__name__} for entry: {model}"
                )
            try:
                app_label, model_name = model.split('.')
                if not app_label or not model_name:
                    raise ValueError
                validated_models.append(f"{app_label}.{model_name}".lower())
            except ValueError:
                raise ValueError(
                        f"Invalid skip_models entry: {model}. "
                        "Format should be 'app_label.ModelName' (e.g., 'wagtailmeili_testapp.ReviewPage')"
                )

        return validated_models

    def _get_skipped_models_by_field_value(self, skip_models_by_field_value):  # noqa
        """Lowercase all the keys of models in the dictionary."""
        if not skip_models_by_field_value:
            return {}

        lowered_dict = {}
        for model, attributes in skip_models_by_field_value.items():
            lowered_dict[model.lower()] = attributes

        logger.info(f"skip_models_by_field_value is now: {lowered_dict}")
        return lowered_dict

    def reset_index(self):
        """Reset the index through the rebuilder."""
        rebuilder = self.get_rebuilder()
        if rebuilder is not None:
            try:
                rebuilder.reset_index(self)
            except Exception:
                raise NotImplementedError(f"{rebuilder.__name__} does not implement 'reset_index'.")

    def delete_all_indexes(self):
        """Delete all indexes from Meilisearch."""
        try:
            rebuilder = self.get_rebuilder()
            if rebuilder is not None:
                rebuilder.delete_all_indexes(self)
        except Exception:
            raise NotImplementedError(f"{rebuilder.__name__} does not implement a 'delete_all_indexes'.")

    def _search(self, query_compiler_class, query, model_or_queryset, **kwargs) -> BaseSearchResults:
        """Override the method from BaseSearchBackend."""
        # Find model/queryset
        if isinstance(model_or_queryset, QuerySet):
            model = model_or_queryset.model
            queryset = model_or_queryset
        else:
            model = model_or_queryset
            queryset = model_or_queryset.objects.all()

        # Model must be a class that is in the index
        if not class_is_indexed(model):
            return MeilisearchEmptySearchResults()

        # Search
        opt_params = kwargs.pop("opt_params", {})
        search_query_compiler = query_compiler_class(queryset, query, **kwargs)

        # Set the search params such as page number and hits per page
        if opt_params:
            search_query_compiler.set_opt_params(opt_params)

        # Check the query
        search_query_compiler.check()

        return self.results_class(self, search_query_compiler)

    def search(self, query, model_or_queryset, fields=None, operator=None, order_by_relevance=True, opt_params=None,):
        """Search for a query string in the index.

        from the BaseSearchBackend.search() method we add the opt_params parameter.

        """
        return self._search(
            self.query_compiler_class,
            query,
            model_or_queryset,
            fields=fields,
            operator=operator,
            order_by_relevance=order_by_relevance,
            opt_params=opt_params,
        )


SearchBackend = MeilisearchBackend
