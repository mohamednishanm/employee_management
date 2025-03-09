from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get a value from a dictionary by key"""
    key = int(key) if isinstance(key, str) and key.isdigit() else key
    return dictionary.get(key)