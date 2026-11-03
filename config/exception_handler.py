from rest_framework.views import exception_handler
from .application_logger import ApplicationLogger


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        ApplicationLogger.exception(f"Unhandled API error: {exc}")
        return None

    errors = response.data
    message = "Request failed."

    if isinstance(errors, dict) and "detail" in errors:
        message = str(errors["detail"])
        errors = None

    response.data = {
        "status": "error",
        "message": message,
        "data": None,
        "errors": errors,
    }
    return response