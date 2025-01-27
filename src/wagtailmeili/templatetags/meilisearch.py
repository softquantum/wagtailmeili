from django import template

register = template.Library()


@register.filter(name="get_matches_position")
def get_matches_position(result):
    return result["_matchesPosition"]  # noqa
