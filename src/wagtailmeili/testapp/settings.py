import os
from pathlib import Path
from decouple import config

SECRET_KEY = "django-insecure-test-key"
DEBUG = True

BASE_DIR = Path(__file__).resolve().parent.parent.parent

if config("TESTS_USE_IN_MEMORY_DATABASE", True, cast=bool) is True:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

INSTALLED_APPS = [
    "wagtailmeili",
    "wagtailmeili.testapp",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

ROOT_URLCONF = "wagtailmeili.testapp.urls"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ALLOWED_HOSTS = ["*"]

WAGTAIL_SITE_NAME = "Test Site"
WAGTAILSEARCH_BACKENDS = {
    "meilisearch": {
        "BACKEND": "wagtailmeili.backend",
        "HOST": config("MEILISEARCH_URL", "http://localhost"),
        "PORT": config("MEILISEARCH_PORT", 7700, cast=int),
        "MASTER_KEY": config("MEILISEARCH_MASTER_KEY", "correctMasterKey"),
        "SKIP_MODELS": ["wagtailmeili_testapp.reviewpage"],
        "SKIP_MODELS_BY_FIELD_VALUE": {
            "wagtailmeili_testapp.MoviePage": {
                "field": "title",
                "value": "Return of the Jedi",
            },
        },
    },
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    },
}

WAGTAILADMIN_BASE_URL = config("WAGTAILADMIN_BASE_URL", "http://example.com")

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), "media")
STATIC_ROOT = os.path.join(os.path.dirname(__file__), "static")

USE_TZ = True
TIME_ZONE = "UTC"
USE_I18N = True
LANGUAGE_CODE = "en-us"
