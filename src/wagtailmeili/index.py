import logging
from typing import Optional, Any

from django.core.serializers import serialize
from django.db.models import Manager, Model, QuerySet
from django.utils.encoding import force_str
from enum import StrEnum, auto
from meilisearch import Client
from meilisearch.task import TaskInfo
from meilisearch.errors import MeilisearchApiError
from wagtail.models import Collection, Page
from wagtail.search import index as wagtail_index
from wagtail.search.index import class_is_indexed

from wagtailmeili.utils import check_for_task_successful_completion, model_is_skipped


logger = logging.getLogger(__name__)


class IndexOperationStatus(StrEnum):
    SKIPPED: str = auto()
    IS_NOT_INDEXED: str = auto()


class MeilisearchIndex:
    """Class for MeiliSearch indexes based on NullIndex class interfaces.

    Meilisearch uses the term "index" to refer to a group of documents with associated settings.
    So basically an index is a searchable model in Wagtail.  It is comparable to a table in SQL.
    An index is defined by a name (uid) and contains the following information:
    - One primary key
    - Customizable settings
    - An arbitrary number of documents

    Features:
    - Model Skipping: Supports skipping specific models through the backend's skip_models list.
      Models in this list will not be indexed.
    - Field-based Skipping: Additional control through skip_models_by_field_value for
      conditional skipping based on model fields values.

    TODO: "id" may not be the primary key of the model yes/no ?
    self.primary_key = model._meta.pk.name

    """

    def __init__(self, backend, model):
        self.backend = backend
        self.client = backend.client
        self.model = model
        if model._meta.proxy:
            base_model = model._meta.proxy_for_model  # noqa E501
            self._name = (
                base_model._meta.app_label.lower() + "_" + base_model.__name__.lower()
            )  # noqa E501
        else:
            self._name = model._meta.app_label.lower() + "_" + model.__name__.lower()  # noqa E501
        self.name = self._name
        self.primary_key = "id"
        self.documents = []
        self.index = self.get_index(self.name)

    def _is_not_indexable(self, model) -> IndexOperationStatus | None:
        """Validate if the model should be indexed."""
        if not class_is_indexed(model):
            return IndexOperationStatus.IS_NOT_INDEXED
        if model_is_skipped(model, self.backend.skip_models):
            return IndexOperationStatus.SKIPPED
        return None

    def get_index(self, uid) -> Optional[Client.index]:
        """Get an index from MeiliSearch.

        client.index(uid) create a local reference to an index identified by uid,
        without doing an HTTP call. It returns a meilisearch.Index class.
        """
        self.index = self.client.index(uid)

        return self.client.index(uid)

    def add_model(self, model) -> Any | None:
        """Add an index: a group of documents with associated settings.

        This method is used in update_index.py and therefore its arguments should not change.

        Returns:
                Client.index if the index is successfully created and configured, else None.

        """

        if self._is_not_indexable(model):
            return None

        try:
            task = self.client.create_index(
                uid=self.name, options={"primaryKey": self.primary_key}
            )
            logger.info(
                f"Creating index '{self.name}' by adding model. Task UID: {task.task_uid}"
            )
            if not check_for_task_successful_completion(
                self.client, task_uid=task.task_uid, timeout=300
            ):
                logger.error(f"Index creation for '{self.name}' was not successful.")
                return None
            self.update_index_settings()
            return self.client.index(self.name)

        except MeilisearchApiError as e:
            logger.error(f"add_model: Error creating index {self.name}: {e}")

        return None

    def add_item(self, item) -> None:
        """Add a document to the index.

        If the index does not exist: If you try to add documents or settings to an index
        that does not already exist, Meilisearch will automatically create it for you.
        https://www.meilisearch.com/docs/learn/getting_started/indexes#implicit-index-creation

        """
        document = self.prepare_documents(self.model, items=item)

        if document:
            try:
                # Check if index exists and has documents
                has_documents = self.index.get_documents().total > 0
                if has_documents:
                    self.index.update_documents(documents=document)
                else:
                    self.index.add_documents(documents=document)
            except MeilisearchApiError as e:
                if "index_not_found" in str(e):
                    # Index doesn't exist, create it by adding documents
                    self.index.add_documents(documents=document)
                else:
                    logger.error(f"Error adding/updating document: {e}")
                    raise

    def add_items(self, model, items) -> TaskInfo | None:
        """Add a list of documents (items) to the index."""
        # update_index.py requires add_items to have these two arguments (model, chunk)
        documents = self.prepare_documents(model, items=items)
        taskinfo = None

        if len(documents) > 0:
            try:
                # Check if index exists and has documents
                has_documents = self.index.get_documents().total > 0
                if has_documents:
                    taskinfo = self.index.update_documents(documents=documents)
                else:
                    taskinfo = self.index.add_documents(documents=documents)
            except MeilisearchApiError as e:
                if "index_not_found" in str(e):
                    # Index doesn't exist, create it by adding documents
                    taskinfo = self.index.add_documents(documents=documents)
                else:
                    logger.error(f"Error adding/updating documents: {e}")
                    raise

        return taskinfo

    def serialize_value(self, value) -> str | list | dict:
        """Make sure `value` is something we can save in the index."""
        if not value:
            return ""
        elif isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join(self.serialize_value(item) for item in value)
        if isinstance(value, dict):
            return ", ".join(self.serialize_value(item) for item in value.values())
        if isinstance(value, QuerySet):
            # is it worth it or should I return an empty value?
            return serialize("json", value)
        if isinstance(value, Manager):
            # is it worth it or should I return an empty value?
            return [self.serialize_value(item) for item in value.all()]
        if isinstance(value, Collection):
            # is it worth it or should I return an empty value?
            return {"id": value.id, "name": value.name}
        if callable(value):
            return force_str(value())
        return str(value)

    def prepare_documents(self, model, items) -> list:
        """Prepare documents for indexing."""
        documents = []
        search_fields = model.get_search_fields()

        if not isinstance(items, list):
            items = [items]

        for item in items:
            if self._should_skip(item, model, self.backend.skip_models_by_field_value):
                continue

            document = self._process_model_instance(instance=item, fields=search_fields)
            if document:
                documents.append(document)

        return documents

    def _should_skip(self, item, model, skipped_models_by_field_value):
        """Check if an item should be skipped based on the model and skip_models_by_field_value."""

        if model_is_skipped(model, self.backend.skip_models):
            return True

        model_key = f"{model._meta.app_label}.{model.__name__}".lower()  # noqa E501
        model_attributes = skipped_models_by_field_value.get(model_key)
        if isinstance(item, Page) and not item.live:
            logger.info(f"Skipping {model.__name__} {item.id} because it is not live")
            return True

        if model_attributes:
            attribute_value = getattr(item, model_attributes["field"], None)
            if attribute_value == model_attributes["value"]:
                logger.info(
                    f"Skipping {model.__name__} {item.id} because {model_attributes['field']} is {model_attributes['value']}"
                )
                return True
        return False

    def _process_model_instance(self, instance, fields) -> dict | None:
        """Recursively process a model instance for indexing."""
        # exclude draft or unpublished pages for the instances with a live attribute
        if getattr(instance, "live", True) is False:
            return None

        document = {
            "id": instance.pk
        }  # TODO: "id" may not be the primary key of the model?
        for field in fields:
            field_name = field.field_name
            field_value = getattr(instance, field_name, None)

            if isinstance(field, wagtail_index.SearchField):
                document[field_name] = self.serialize_value(field_value)
            elif isinstance(field, wagtail_index.FilterField):
                document[field_name] = self.serialize_value(field_value)
            elif isinstance(field, wagtail_index.RelatedFields):
                if isinstance(
                    field_value, (Manager, QuerySet)
                ):  # ManyToManyField and OneToManyField
                    related_objects = field_value.all()
                    document[field_name] = [
                        self._process_model_instance(obj, field.fields)
                        for obj in related_objects
                    ]
                elif isinstance(field_value, Model):  # ForeignKey
                    document[field_name] = self._process_model_instance(
                        field_value, field.fields
                    )

        return document

    def delete_item(self, item_or_pk) -> TaskInfo | None:
        """Enhanced delete with better error handling."""
        try:
            # Handle both model instances and primary keys
            if hasattr(item_or_pk, "pk"):
                pk = item_or_pk.pk
            else:
                pk = item_or_pk

            task = self.index.delete_document(pk)
            logger.info(f"Deleted document {pk} from index {self.name}")
            return task

        except MeilisearchApiError as e:
            if "document_not_found" in str(e):
                logger.warning(f"Document {pk} not found in index {self.name}")
                return None
            else:
                logger.error(f"Error deleting document {pk}: {e}")
                raise

    def bulk_delete_items(self, item_pks) -> TaskInfo | None:
        """Bulk delete multiple items by primary key."""
        try:
            if not item_pks:
                return None

            # Ensure we have a list of primary keys
            pk_list = [pk.pk if hasattr(pk, "pk") else pk for pk in item_pks]

            task = self.index.delete_documents(pk_list)
            logger.info(f"Bulk deleted {len(pk_list)} documents from index {self.name}")
            return task

        except MeilisearchApiError as e:
            logger.error(f"Error bulk deleting documents: {e}")
            raise

    def cleanup_stale_documents(self, live_pks) -> None:
        """Remove documents that shouldn't be in the index."""
        try:
            # Get all document IDs currently in index
            current_docs = self.index.get_documents(fields=["id"])
            current_index_ids = {doc["id"] for doc in current_docs.results}

            # Convert live_pks to set of strings (MeiliSearch uses string IDs)
            live_ids = {str(pk) for pk in live_pks}

            # Find stale documents
            stale_ids = current_index_ids - live_ids

            if stale_ids:
                self.bulk_delete_items(list(stale_ids))
                logger.info(f"Cleaned up {len(stale_ids)} stale documents")

        except Exception as e:
            logger.error(f"Failed to cleanup stale documents: {e}")

    def update_index_settings(self) -> TaskInfo:
        """Update index settings based on model's search fields.

        Returns:
            TaskInfo | None: The task info if successful, None if an error occurred.

        Raises:
            MeilisearchApiError: If there's an error communicating with Meilisearch
            ValueError: If the settings are invalid

        """
        try:
            searchable_attributes = []
            filterable_attributes = []
            sortable_attributes = []

            def collect_attributes(field_list, parent_field_name="") -> None:
                for field in field_list:
                    field_name = (
                        f"{parent_field_name}.{field.field_name}"
                        if parent_field_name
                        else field.field_name
                    )

                    if isinstance(field, wagtail_index.SearchField):
                        searchable_attributes.append(field_name)
                    elif isinstance(field, wagtail_index.FilterField):
                        filterable_attributes.append(field_name)
                    elif isinstance(field, wagtail_index.RelatedFields):
                        collect_attributes(
                            field_list=field.fields, parent_field_name=field_name
                        )

            collect_attributes(self.model.get_search_fields())
            if hasattr(self.model, "sortable_attributes"):
                sortable_attributes = self.model.sortable_attributes
                logger.info(f"Sortable attributes added for index {self.name}")

            if hasattr(self.model, "ranking_rules"):
                self.backend.ranking_rules.extend(self.model.ranking_rules)
                logger.info(
                    f"Ranking rules {self.model.ranking_rules} added for index {self.name}"
                )
                logger.info(f"Ranking rules are now {self.backend.ranking_rules}.")

            index_settings = {
                "rankingRules": self.backend.ranking_rules,
                "stopWords": self.backend.stop_words,
                "searchableAttributes": searchable_attributes,
                "filterableAttributes": filterable_attributes,
                "sortableAttributes": sortable_attributes,
                "typoTolerance": {
                    "enabled": True,
                    "minWordSizeForTypos": {"oneTypo": 3, "twoTypos": 7},
                    "disableOnWords": [],
                    "disableOnAttributes": [],
                },
            }

            taskinfo = self.index.update_settings(index_settings)
            logger.info(f"Settings updated for index {self.name}")
            return taskinfo

        except MeilisearchApiError as err:
            error_message = f"Error updating settings for index {self.name}"
            if hasattr(err, "code"):
                error_message += f" (Error code: {err.code})"
            if hasattr(err, "message"):
                error_message += f": {err.message}"
            else:
                error_message += f": {str(err)}"

            logger.error(error_message)

            if hasattr(err, "__dict__"):
                logger.debug(f"Detailed error information: {err.__dict__}")
            return None

        except Exception as err:
            logger.error(
                f"Unexpected error updating settings for index {self.name}: {str(err)}"
            )
            logger.exception("Stack trace:")
            return None
