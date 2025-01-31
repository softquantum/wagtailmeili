import logging

from .exceptions import MeiliSearchRebuildException
from .index import MeilisearchIndex
from .utils import check_for_task_successful_completion, is_in_meilisearch
from meilisearch.task import TaskInfo

logger = logging.getLogger("search")


class MeilisearchRebuilder:
    """Class for rebuilding MeiliSearch indexes.

    This class will manage the lifecycle of creating, populating, and swapping indexes in MeiliSearch.
    - start: would initiate the creation of a new index, and store it in the new_index attribute.
    - finish: will manage the transition to the new index.
    - reset_index: not sure what to do with it.
    More information on the MeiliSearch documentation: https://docs.meilisearch.com/guides/advanced_guides/indexes.html
    """

    def __init__(self, index: MeilisearchIndex):
        self.index: MeilisearchIndex = index

    def start(self) -> MeilisearchIndex:
        """Start the rebuild process.

        Returns:
            MeilisearchIndex: The index to be used for rebuilding

        Raises:
            MeiliSearchRebuildException: If there's an error during the start process
        """
        try:
            if is_in_meilisearch(self.index.client, self.index.name):
                new_index_name = f"{self.index.name}_new"
                logger.info(f"Rebuilder: Starting the rebuild with swapping.: {new_index_name}")
                # if the new index already exists, delete it first
                if is_in_meilisearch(self.index.client, new_index_name):
                    task = self.index.client.index(new_index_name).delete()
                    self.index.client.wait_for_task(task.task_uid)
                    succeeded = check_for_task_successful_completion(self.index.client, task.task_uid, timeout=200)
                    if not succeeded:
                        raise MeiliSearchRebuildException(
                            f"Failed to delete existing temporary index {new_index_name}"
                        )
                    logger.info(f"Rebuilder: A ghost Index {new_index_name} has been deleted (status: {succeeded}).")
                # create the {index}_new index
                self.index.name = new_index_name
                self.index.get_index(self.index.name)
            else:
                logger.info("Rebuilder: Starting the rebuild.")
                self.index.get_index(self.index.name)
        except Exception as e:
            error_msg = f"Failed to start rebuild process: {str(e)}"
            logger.error(f"Rebuilder: {error_msg}")
            raise MeiliSearchRebuildException(error_msg) from e

        return self.index

    def finish(self) -> TaskInfo:
        """Finish the rebuild process by swapping indexes if needed.

        Returns:
            TaskInfo: The task information of the last operation performed
                     (either swap or delete operation).

        Raises:
            MeiliSearchRebuildException: If there's an error during the finish process

        """
        logger.info("Rebuilder: Finishing the rebuild.")
        temp_index_name = self.index._name + "_new"  # noqa E501
        task = None

        try:
            if is_in_meilisearch(self.index.client, temp_index_name):
                logger.info("Rebuilder: Swapping indexes.")
                task = self.index.client.swap_indexes([{"indexes": [self.index.name, self.index._name]}])  # noqa E501
                succeeded = check_for_task_successful_completion(self.index.client, task.task_uid, timeout=300)
                logger.info(f"Swap Succeeded? {succeeded}")
                if succeeded:
                    task = self.index.client.index(temp_index_name).delete()   # TODO: harmonize the calls either client.delete_index or index.delete()
                    delete_succeeded = check_for_task_successful_completion(self.index.client, task.task_uid, timeout=200)
                    if delete_succeeded:
                        logger.info(f"Rebuilder: Temporary index {temp_index_name} deleted")
                    else:
                        logger.warning(f"Failed to delete temporary index {temp_index_name}")
                else:
                    raise MeiliSearchRebuildException("Failed to swap indexes")
            return task

        except Exception as e:
            error_msg = f"Error while finishing the rebuild: {str(e)}"
            logger.error(f"Rebuilder: {error_msg}")
            raise MeiliSearchRebuildException(error_msg) from e

    @staticmethod
    def reset_index(backend):
        """Reset the index by deleting all documents from all indexes.

        Raises:
            MeiliSearchRebuildException: If there's an error during the reset process

        """
        try:
            indexes = backend.client.get_indexes()
            for index in indexes['results']:
                task = index.delete_all_documents()
                succeeded = check_for_task_successful_completion(backend.client, task.task_uid, timeout=200)
                if not succeeded:
                    raise MeiliSearchRebuildException(
                            f"Failed to delete documents from index {index.uid}"
                    )

        except Exception as e:
            error_msg = f"Error resetting indexes: {str(e)}"
            logger.error(error_msg)
            raise MeiliSearchRebuildException(error_msg) from e

    @staticmethod
    def delete_all_indexes(backend):
        """Reset the index by deleting all indexes.

        Raises:
            MeiliSearchRebuildException: If there's an error during the deletion process

        """
        try:
            indexes = backend.client.get_indexes()
            for index in indexes['results']:
                task = backend.client.delete_index(index.uid)
                succeeded = check_for_task_successful_completion(backend.client, task.task_uid, timeout=200)
                if not succeeded:
                    raise MeiliSearchRebuildException(
                            f"Failed to delete index {index.uid}"
                    )

        except Exception as e:
            error_msg = f"{str(e)}"
            logger.error(error_msg)
            raise MeiliSearchRebuildException(error_msg) from e
