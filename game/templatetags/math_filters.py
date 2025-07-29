from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide the value by the argument."""
    try:
        return int(value) // int(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def mod(value, arg):
    """Return the modulo of value and argument."""
    try:
        return int(value) % int(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def sub(value, arg):
    """Subtract the argument from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def thousands(value):
    """Format number with thousand separators."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

@register.filter
def lookup(dictionary, key):
    """Look up a key in a dictionary."""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None 