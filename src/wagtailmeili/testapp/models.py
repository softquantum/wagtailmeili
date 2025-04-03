from django.db import models

from wagtail.models import Page
from wagtail.search import index
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

from wagtailmeili.manager import MeilisearchPageManager


class MoviePageIndex(Page):
    # parent page type should be the homepage
    subpage_types = ['wagtailmeili_testapp.MoviePage']
    max_count = 1

    @property
    def movies(self):
        return MoviePage.objects.live().descendant_of(self)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request)
        context['movies'] = self.movies
        return context


class MoviePage(Page):
    overview = models.TextField(blank=True, null=True)
    genres = models.JSONField(blank=True, null=True)
    poster = models.URLField(blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)

    parent_page_types = ['wagtailmeili_testapp.MoviePageIndex']
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel('overview'),
        FieldPanel('genres'),
        FieldPanel('poster'),
        FieldPanel('release_date'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('overview'),
        index.SearchField('poster'),
        index.FilterField('genres'),
        index.FilterField('release_date'),
    ]


class MoviePageWithManager(MoviePage):

    objects = MeilisearchPageManager()

    class Meta:
        proxy = True


class ReviewPage(Page):
    parent_page_types = ['wagtailmeili_testapp.MoviePageIndex']
    subpage_types = []

    movie = models.ForeignKey('wagtailmeili_testapp.MoviePage', on_delete=models.SET_NULL, null=True, blank=True)
    review = RichTextField(null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('movie'),
        FieldPanel('review'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('review'),
    ]


class NonIndexedPage(Page):
    search_fields = []

    class Meta:
        app_label = 'wagtailmeili_testapp'


class NonIndexedModel(models.Model):
    """A regular Django model with no search fields."""

    class Meta:
        app_label = 'wagtailmeili_testapp'


class Author(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'wagtailmeili_testapp'


class RelatedMoviePage(MoviePage):
    author = models.ForeignKey(
        Author,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='movies'
    )
    related_movies = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='related_to'
    )

    search_fields = MoviePage.search_fields + [
        index.RelatedFields('author', [
            index.SearchField('name'),
        ]),
        index.RelatedFields('related_movies', [
            index.SearchField('title'),
        ]),
    ]
