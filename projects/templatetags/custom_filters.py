from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    """Get a value from a dictionary by key"""
    key_str = str(key)
    if dictionary and key_str in dictionary:
        return str(dictionary[key_str])
    return None