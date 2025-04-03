# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),

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

