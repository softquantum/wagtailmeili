# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),

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

