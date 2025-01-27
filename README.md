# Wagtailmeili
[![License](https://img.shields.io/badge/license-BSD-blue.svg?style=flat)](https://opensource.org/licenses/BSD-3-Clause)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A search backend for Wagtail using [MeiliSearch](https://github.com/meilisearch/MeiliSearch).

> [!CAUTION]
> This package is still in development and until version 1.0.0, I will not maintain a DeprecationWarning pattern.
> I built the integration with meilisearch about 2 years ago for a project and decided to make it a public package to improve it and integrate more features.

> [!TIP]  
> If you need support or require help with a Wagtail project, you can hire me 😊

## Requirements
Wagtailmeili requires the following:
- Python >= 3.10
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
add the search backend to your `WAGTAILSEARCH_BACKENDS`
```python
import os

WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtailmeili.backend",
        "HOST":  os.environ.get("MEILISEARCH_HOST", "http://127.0.0.1"),
        "PORT": os.environ.get("MEILISEARCH_PORT", "7700"),
        "MASTER_KEY": os.environ.get("MEILISEARCH_MASTER_KEY", "your-master-key"),
        # "STOP_WORDS": ...
        # "RANKING_RULES: ...
        # "SKIP_MODELS": ...
        # "SKIP_MODELS_BY_FIELD_VALUE": ...
    },
}
```
## Features
### Default search configs
* STOP_WORDS: see defaults in [settings.py](src/wagtailmeili/settings.py)
* RANKING_RULES: see defaults in [settings.py](src/wagtailmeili/settings.py)
* SKIP_MODELS: "skip_models" is a list of models that you want to skip from indexing no matter the model setup.
```python
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "SKIP_MODELS": ["app_label.Model1", "app_label.Model2",],
        # ...
    }
}
```
* SKIP_MODELS_BY_FIELD_VALUE: A convenient way to skip instances based on attributes
```python
WAGTAILSEARCH_BACKENDS = {
    "default": {
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

To declare **_sortable attributes_** or add **_ranking rules_** for the model, just add, for example:
```python
from wagtail.models import Page


class MySuperPage(Page):
    """A Super Page to do incredible things."""
    
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

## Roadmap (unsorted)
- Adding tests
- Exploring Meilisearch and bringing more of its features for Wagtail
- Getting a leaner implementation (looking at Autocomplete and rebuilder)
- Giving more love to the Sample project with a frontend

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

## Contributions
Welcome to all contributions!

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
pyest 
```
or with tox however, I still need to fix migrations in the testapp to be wagtail 5.2 compliant
```
tox
```

## License
This project is released under the [3-Clause BSD License](LICENSE).
