from decimal import Decimal, InvalidOperation

from django import template
from django.utils.dateparse import parse_datetime

register = template.Library()

RISK_COLOURS = {"low": "success", "medium": "warning", "high": "danger"}


@register.filter
def gain_class(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "text-muted"

    if number > 0:
        return "text-success"

    if number < 0:
        return "text-danger"

    return "text-muted"


@register.filter
def risk_colour(label):
    return RISK_COLOURS.get(label, "secondary")


@register.filter
def as_percent(value):
    if value is None or value == "":
        return "-"

    return f"{float(value) * 100:.1f}%"


@register.filter
def to_datetime(value):
    if not value:
        return None

    return parse_datetime(str(value))