# Wagtailmeili
[![Test](https://github.com/softquantum/wagtailmeili/actions/workflows/test.yml/badge.svg?event=push&branch=main)](https://github.com/softquantum/wagtailmeili/actions?query=workflow%3ATest+event%3Apush+branch%3Amain)
[![Version](https://img.shields.io/pypi/v/wagtailmeili.svg?style=flat)](https://pypi.python.org/pypi/wagtailmeili/)
[![codecov](https://codecov.io/gh/softquantum/wagtailmeili/graph/badge.svg?token=QY0HJ9L6N5)](https://codecov.io/gh/softquantum/wagtailmeili)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/license-BSD-blue.svg?style=flat)](https://opensource.org/licenses/BSD-3-Clause)

A search backend for Wagtail using [MeiliSearch](https://github.com/meilisearch/MeiliSearch).

> [!CAUTION]
> This package is still in development and until version 1.0.0, I will not maintain a DeprecationWarning pattern.
> I built the integration with meilisearch about 2 years ago for a project and decided to make it a public package to improve it and integrate more features.

> [!TIP]  
> If you need support or require help with a Wagtail project, you can hire me 😊

## Introduction
en - https://softquantum.com/resources/wagtailmeili-integrating-a-blazing-fast-search-engine-with-wagtail

fr - https://softquantum.com/fr/ressources/wagtailmeili-integrer-un-moteur-de-recherche-rapide-avec-wagtail/

## Requirements
Wagtailmeili requires the following:
- Python >= 3.11
- Wagtail >= 5.2

## Installation

### In your Wagtail project
#### Configure your MeiliSearch instance in your `settings.py` file.
Install Meilisearch python client e.g., using pip
```shell
  pip install meilisearch
```
Add `wagtailmeili` to your `INSTALLED_APPS`
```python
INSTALLED_APPS = [
    # ...
    "wagtailmeili",
    # ...
]
```
add the search backend 'meilisearch' to your `WAGTAILSEARCH_BACKENDS`
> [!CAUTION] 
> Leave the 'default' backend for the admin as you don't want to depend only on what was indexed in meilisearch
> Different use cases to consider so still work in progress. 
```python
import os

WAGTAILSEARCH_BACKENDS = {
    "meilisearch": {
        "BACKEND": "wagtailmeili.backend",
        "HOST":  os.environ.get("MEILISEARCH_HOST", "http://127.0.0.1"),
        "PORT": os.environ.get("MEILISEARCH_PORT", "7700"),
        "MASTER_KEY": os.environ.get("MEILISEARCH_MASTER_KEY", "your-master-key"),
        # "STOP_WORDS": ...
        # "RANKING_RULES: ...
        # "SKIP_MODELS": ...
        # "SKIP_MODELS_BY_FIELD_VALUE": ...
    },
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}
```
## Features
### Default search configs
* STOP_WORDS: see defaults in [settings.py](src/wagtailmeili/settings.py)
* RANKING_RULES: see defaults in [settings.py](src/wagtailmeili/settings.py)
* SKIP_MODELS: "skip_models" is a list of models that you want to skip from indexing no matter the model setup.
```python
WAGTAILSEARCH_BACKENDS = {
    "meilisearch": {
        "SKIP_MODELS": ["app_label.Model1", "app_label.Model2",],
        # ...
    }
}
```
* SKIP_MODELS_BY_FIELD_VALUE: A convenient way to skip instances based on attributes
```python
WAGTAILSEARCH_BACKENDS = {
    "meilisearch": {
        # add this to not index pages that are not published for example
        "SKIP_MODELS_BY_FIELD_VALUE": {
            "wagtailmeili_testapp.MoviePage": {
                "field": "live",
                "value": False,
            },
        },
        # ...
    }
}
```

### Model fields

In any model you will be doing a search on with Meilisearch, add the page or model manager.  
It will use the correct backend when doing something like `MySuperPage.objects.search()`.
```python
from wagtail.models import Page
from django.db import models
from wagtailmeili.manager import MeilisearchPageManager, MeilisearchModelManager

class MySuperPage(Page):
    """A Super Page to do incredible things indexed in Meilisearch."""
 
    objects = MeilisearchPageManager()

class MySuperModel(models.Model):
    """A Super Model to do incredible things indexed in Meilisearch."""
 
    objects = MeilisearchModelManager()
```

To declare **_sortable attributes_** or add **_ranking rules_** for the model, just add, for example:
```python
from wagtail.models import Page


class MySuperPage(Page):
    """A Super Page to do incredible things indexed in Meilisearch."""
    
    sortable_attributes = [
        "published_last_timestamp", 
        # ...
    ]
    ranking_rules = [
        "published_last_timestamp:desc",
        # ...
    ]
```

### Template Tag filter
```html
{% load meilisearch %}

{% get_matches_position result %}
```

## Index Cleanup

Wagtailmeili automatically handles cleanup of stale documents from your MeiliSearch indexes to ensure search results remain accurate and up-to-date.

### Automatic Cleanup

**Real-time Cleanup**: When items are deleted or unpublished, they are automatically removed from the search index via Django signals.

**Rebuild Cleanup**: When running `python manage.py update_index`, stale documents are automatically detected and removed.

**Smart Detection**: The system automatically handles both regular models and Page models with `live` field detection.

### Manual Cleanup

Use the management command for manual cleanup operations:

```bash
# Clean all indexes (dry-run mode)
python manage.py cleanup_search_index --dry-run

# Clean all indexes
python manage.py cleanup_search_index

# Clean specific model
python manage.py cleanup_search_index --model wagtailmeili_testapp.MoviePage

# Verbose output
python manage.py cleanup_search_index --verbosity 2
```

### Programmatic Cleanup

You can also perform cleanup operations programmatically:

```python
from wagtail.search.backends import get_search_backend

# Get the MeiliSearch backend
backend = get_search_backend('meilisearch')
index = backend.get_index_for_model(MyModel)

# Remove specific items
index.delete_item(item_id)

# Bulk remove multiple items
index.bulk_delete_items([id1, id2, id3])

# Clean up stale documents
live_ids = MyModel.objects.filter(live=True).values_list('pk', flat=True)
index.cleanup_stale_documents(live_ids)
```

### Configuration

The cleanup system respects your existing configuration:

- **SKIP_MODELS**: Models in this list won't be cleaned up
- **SKIP_MODELS_BY_FIELD_VALUE**: Field-based skipping is honored during cleanup
- **Page Models**: Only live pages (`live=True`) are considered valid for Page models

## Roadmap before 1.0.0 (unsorted)
- -[x] ~~Adding tests~~ (v0.3.3)
- -[x] ~~Cleaning up index if pages are unpublished or models deleted~~ (v0.4.0)
- -[ ] Exploring Meilisearch and bringing more of its features for Wagtail
- -[ ] Getting a leaner implementation (looking at Autocomplete and rebuilder)
- -[ ] Giving more love to the Sample project with a frontend
- -[ ] official documentation

## Sample Project: WMDB
The Wagtail Movie Database (WMDB) is a sample project for testing purposes. To run the project, follow these steps:
1. start the local meilisearch instance
```shell
meilisearch --master-key=<your masterKey>
```
2. copy the directory wagtail_moviedb wherever you want
3. create a virtualenv and activate it (instructions on linux/macOS)
```shell
python -m venv .venv
source .venv/bin/activate
```
4. install the dependencies
```shell
pip install -r requirements.txt
```
5. add an .env file
```dotenv
MEILISEARCH_MASTER_KEY="your masterKey"
```
6. apply migrations
```shell
python manage.py migrate
```
7. Create a superuser (optional)
```shell
python manage.py createsuperuser
```
8. load movies & start local web server
```shell
python manage.py load_movies
python manage.py runserver
```
9. visit your meilisearch local instance: https://127.0.0.1:7700, give it your master-key.  You should see some movies loaded.
10. update index (optional):
```shell
python manage.py update_index
```

## Development

### Development Setup

This package uses [flit](https://flit.pypa.io/en/latest/) for both local development and publishing.

1. Install flit (if not already available):
```shell
# Via pip
pip install flit

# Via pyenv (if you have a Python version with flit pre-installed)
# flit may already be available in your pyenv Python installation
```

2. Install the package locally for development:
```shell
# Using pip
pip install "pip>=21.3"
pip install -e '.[dev]' -U

# Using flit
flit install -s
```
For more information on installing and using flit, see the [official flit documentation](https://flit.pypa.io/en/latest/install.html).

## Contributions
Welcome to all contributions and reviews!

### Prerequisites
- Install Meilisearch locally following their [documentation](https://www.meilisearch.com/docs/learn/self_hosted/install_meilisearch_locally)
- Start Meilisearch instance in your favorite terminal

```shell
meilisearch --master-key correctmasterkey
```

### Install
To make changes to this project, first clone this repository:

```sh
git clone git@github.com:softquantum/wagtailmeili.git
cd wagtailmeili
```

With your preferred virtualenv activated, install testing dependencies:
#### Using pip

```sh
pip install "pip>=21.3"
pip install -e '.[dev]' -U
```
### How to run tests

You can run tests as shown below:
```shell
pytest 
```
or with tox
```
tox
```

## Disclaimer
- ✅ This project is to experiment with my dev experience and improve my skills. 
- ✅ It is, since v0.3, developed in an **augmented development setup** (JetBrains Pycharm, Claude Code with custom commands and configs)
- ✅ I commit to have a test suite that makes sense (reviews are welcome)
- ✅ The project is used in production in real projects: no shortcuts for quality standards, so if you find a bug please report it.
- ✅ It is an open source project so you can hire me for support ☕️

## License
This project is released under the [3-Clause BSD License](LICENSE).
