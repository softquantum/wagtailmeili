# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),

## [0.6.0] - 2026-10-04
### Added
- **Wagtail 8.0 support**, tested with Django 5.2, 6.0 and 6.1
- **Custom base page models:** unpublished pages are skipped for page types built on a swapped base page model (`WAGTAIL_PAGE_MODEL`, Wagtail 8.0+)

### Removed
- Support for Wagtail < 7.0 and Django < 5.2
- Support for Python 3.11

### Fixed
- **Stale document cleanup:** `cleanup_search_index`, `MeilisearchIndex.cleanup_stale_documents()` and `MeilisearchRebuilder.rebuild_index_for_model()` deleted nothing because of an invalid call to the Meilisearch client. They now read all document IDs (paginated) and remove the stale ones
- **`update_index` with `SKIP_MODELS`:** the command no longer crashes on models listed in `SKIP_MODELS`
- `cleanup_search_index` skips models without an index instead of reporting an error for them
- **Proxy models:** a `SKIP_MODELS_BY_FIELD_VALUE` rule set on a model now also applies to items indexed through its proxy models, and listing a model in `SKIP_MODELS` also skips its proxy models. Previously `update_index` indexed the skipped items through the proxy, which shares the same index
- Test configuration no longer references `RemovedInDjango60Warning`, which broke pytest on Django 6.x

## Tests
- **Tested** with Wagtail 7.0, 7.4 and 8.0, Python 3.12 to 3.14 and Meilisearch 1.54
- **Added** integration tests against a real Meilisearch instance for stale document cleanup, `update_index`, unpublishing, and the absence of requests for models without an index (#2)
- **Replaced** mock-based cleanup tests that did not match the Meilisearch client
- **Added** a tox environment pinned to the minimum supported Meilisearch client (0.29.0)
- **CI:** the Python matrix is now 3.12, 3.13 and 3.14

## [0.5.2] - 2025-11-14
### Added
- **Wagtail 7.2 support:** `get_key()`, `refresh()` and `reset()` on `MeilisearchIndex` and `NullIndex` (modelsearch `BaseIndex` interface)

## [0.5.1] - 2025-11-08
### Fixed
- **Proxy models:** Avoid duplicate index creation attempts for proxy models

## [0.5.0] - 2025-11-07
###  Changed
- **Removed unnecesary signal integration**
  - Removed custom `post_delete` signal handler that was causing issues
  - Kept custom `page_unpublished` signal handler for proper unpublished page cleanup because Wagtail fires `post_save` (not `post_delete`) when pages are unpublished
- **in MeilisearchBackend**
  - `get_index_for_model()` now returns `NullIndex` instance for non-indexed models and models in `SKIP_MODELS`

### Fixed
- **Performance Issue**
  - MeiliSearch was receiving unnecessary delete requests for non-existent indexes
  - Root cause: `get_index_for_model()` always returned an index object, even for non-indexed models

## Tests
- **Tested** with wagtail 7.2 and python 3.14
- **Improved** testing environment setup

## [0.4.0] - 2025-01-07
### Added
- **Automatic Index Cleanup**: Comprehensive solution for removing stale documents from MeiliSearch indexes
- **Real-time Signal Handling**: Automatic cleanup when items are deleted or unpublished via Django signals
- **Enhanced Index Operations**: New `delete_item()`, `bulk_delete_items()`, and `cleanup_stale_documents()` methods in MeilisearchIndex
- **Rebuilder Cleanup**: Enhanced rebuilder with automatic stale document removal during index rebuilds
- **Management Command**: New `cleanup_search_index` command for manual cleanup operations with dry-run support
- **Test-Driven Implementation**: Comprehensive test suite with 23+ tests covering all cleanup scenarios

### Fixed
- **Index Creation Race Conditions**: Fixed 404 errors when accessing index settings before index creation
- **Integration Test Stability**: Resolved database table creation issues with dynamic test models
- **Manager Test Reliability**: Enhanced manager tests with proper index setup and error handling
- **Mock Specifications**: Improved test mocks with proper `spec` parameters for better type safety

### Enhanced
- **Error Handling**: Better error handling in `add_item()` and `add_items()` methods for missing indexes
- **Signal Integration**: Automatic signal connection through Django app configuration
- **Test Coverage**: Significantly improved test coverage for cleanup and core functionality

## [0.3.3] - 2025-04-03
### Fixed
- MeilisearchAutocompleteQueryCompiler had the wrong matching strategy
- MeilisearchAutocompleteQueryCompiler str query type

### Changed
Make sure you add either MeilisearchModelManager or MeilisearchPageManager for the models you will search with meilisearch

- WAGTAILSEARCH_BACKENDS needs a meilisearch and keep the default to database (see README)


## [0.3.0] - 2025-02-13
### Added
- Paginator
- Managers for to make it easier to use the search engine from the models
- Tests

## [0.2.0] - 2025-02-02
### Added
- Test coverage
- Better error handling

### Changed
- Dropped support for Python 3.10: don't use 3.10.

## [0.1.1] - 2025-01-27
### Added
- First wrap of the project into this package

