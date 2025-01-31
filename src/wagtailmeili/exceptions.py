class MeiliSearchIndexException(Exception):
    """Exception raised when there is an error during indexing."""

    pass


class MeiliSearchConnectionException(Exception):
    """Exception raised when there is an error during connection to MeiliSearch."""

    pass


class MeiliSearchRebuildException(Exception):
    """Custom exception for rebuild process failures."""
    pass


class MeiliSearchModelIndexException(Exception):
    """Exception raised when there is an error getting a model Index."""

    pass


class MeilisearchIndexCreationWarning(Warning):
    """Exception raised when there is an error creating a MeiliSearch Index."""

    pass


class WagtailSearchBackendDeprecationWarning(Warning):
    """Warning raised when using a deprecated Wagtail search backend function or class."""

    pass
