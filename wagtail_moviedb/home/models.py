from django.db import models

from wagtail.models import Page
from wagtail.search import index
from wagtail.admin.panels import FieldPanel

class HomePage(Page):
    subpage_types = ['home.MoviePage']

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

    parent_page_types = ['home.HomePage']
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel('title'),
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