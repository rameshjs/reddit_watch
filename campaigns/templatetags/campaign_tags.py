from django import template

register = template.Library()

@register.filter
def get_hours(seconds):
    try:
        return int(seconds) // 3600
    except (ValueError, TypeError):
        return 0

@register.filter
def get_minutes(seconds):
    try:
        return (int(seconds) % 3600) // 60
    except (ValueError, TypeError):
        return 0

@register.filter
def get_seconds(seconds):
    try:
        return int(seconds) % 60
    except (ValueError, TypeError):
        return 0
