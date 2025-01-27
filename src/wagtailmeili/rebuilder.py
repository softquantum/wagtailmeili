import logging

from .index import MeilisearchIndex
from .utils import check_for_task_successful_completion, is_in_meilisearch

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
        self.index = index

    def start(self) -> MeilisearchIndex:
        try:
            if is_in_meilisearch(self.index.client, self.index.name):
                new_index_name = f"{self.index.name}_new"
                logger.info(f"Rebuilder: Starting the rebuild with swapping.: {new_index_name}")
                # if the new index already exists, delete it first
                if is_in_meilisearch(self.index.client, new_index_name):
                    task = self.index.client.index(new_index_name).delete()
                    succeeded = check_for_task_successful_completion(self.index.client, task.task_uid, timeout=200)
                    logger.info(f"Rebuilder: A ghost Index {new_index_name} has been deleted (status: {succeeded}).")
                # create the {index}_new index
                self.index.name = new_index_name
                self.index.get_index(self.index.name)
            else:
                logger.info("Rebuilder: Starting the rebuild.")
                self.index.get_index(self.index.name)
        except Exception as e:
            logger.error(f"Rebuilder: Error while getting index: {e}")
        return self.index

    def finish(self):
        logger.info("Rebuilder: Finishing the rebuild.")
        logger.info(f"Rebuilder: Checking if the new index exists: {self.index._name}_new")
        try:
            if is_in_meilisearch(self.index.client, self.index._name + "_new"):
                logger.info("Rebuilder: Swapping indexes.")
                task = self.index.client.swap_indexes([{"indexes": [self.index.name, self.index._name]}])  # noqa E501
                succeeded = check_for_task_successful_completion(self.index.client, task.task_uid, timeout=300)
                logger.info(f"Swap Succeeded? {succeeded}")
                if succeeded:
                    self.index.client.index(self.index._name + "_new").delete()   # noqa E501
                    logger.info(f"Rebuilder: Swap index {self.index._name}_new deleted")  # noqa E501
        except Exception as e:
            logger.error(f"Rebuilder: Error while finsihing the rebuild: {e}")

    @staticmethod
    def reset_index(backend):
        """Reset the index by deleting all documents from all indexes."""
        try:
            indexes = backend.client.get_indexes()
            for index in indexes['results']:
                index.delete_all_documents()

        except Exception as err:
            logger.error(f"Error resetting indexes: {err}")

    @staticmethod
    def delete_all_indexes(backend):
        """Reset the index by deleting all indexes."""
        try:
            indexes = backend.client.get_indexes()
            for index in indexes['results']:
                backend.client.delete_index(index.uid)

        except Exception as err:
            logger.error(f"Error resetting indexes: {err}")