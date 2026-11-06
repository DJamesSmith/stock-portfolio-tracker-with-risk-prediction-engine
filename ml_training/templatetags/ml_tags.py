from django import template

register = template.Library()


@register.filter
def duration(value):
    if value is None:
        return "-"

    total_seconds = int(value.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}h {minutes}m"

    if minutes:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


@register.filter
def metric(value):
    if value is None or value == "":
        return "-"

    return f"{float(value):.4f}"