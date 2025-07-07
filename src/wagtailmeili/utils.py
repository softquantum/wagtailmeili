import time
from typing import Type

from django.db.models import Model
from meilisearch import Client
from meilisearch.errors import MeilisearchApiError
from requests import HTTPError


def model_is_skipped(model: Type[Model], skip_models: list[str]) -> bool:
    """Check if a model should be skipped based on the skip_models configuration.

    Args:
        model: The model class to check
        skip_models: List of models as strings identifiers (e.g., "app_label.ModelName")

    Returns:
        bool: True if the model should be skipped, False otherwise

    Raises:
        TypeError: If model is not a Django/Wagtail Model class

    """
    if not skip_models:
        return False

    if not (isinstance(model, type) and issubclass(model, Model)):
        raise TypeError("Expected a Django/Wagtail Model class")

    model_identifier = f"{model._meta.app_label}.{model.__name__}".lower()
    return model_identifier in [item.lower() for item in skip_models]


def check_for_task_successful_completion(client, task_uid, timeout=300):
    """Poll the Meilisearch task status endpoint until the task is completed or failed.

    :param client: The Meilisearch Client object.
    :param task_uid: The task identifier to check the status of.
    :param timeout: The maximum time in seconds to wait for the task to complete.
    :return: True if task completed successfully, False otherwise.
    """
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            print("Timeout exceeded while waiting for task completion.")
            return False

        task = client.get_task(task_uid)

        if task.status == "succeeded":
            break

        if task.status == "failed":
            return False

        time.sleep(0.075)  # Wait 75ms before retrying

    return task.status == "succeeded"


def is_in_meilisearch(client: Client, name: str) -> bool:
    """Check if an index exists in MeiliSearch."""
    try:
        client.get_index(name)  # the index must exist to be returned
    except MeilisearchApiError:
        return False
    except HTTPError:
        return False

    return True


def transform_to_int(value):
    """Transform a value to an integer if possible."""
    if isinstance(value, list):
        try:
            if value and isinstance(value[0], list):
                # If the value is a list of lists, convert to integers one by one.
                return [int(item) for sublist in value for item in sublist if item.isdigit()]
            else:
                # If the value is a simple list, convert to integers as usual.
                return [int(item) for item in value if item.isdigit()]
        except AttributeError:
            pass
    elif isinstance(value, str):
        return int(value) if value.isdigit() else value
    return value
