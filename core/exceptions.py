from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler
from core.application_logger import ApplicationLogger


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        ApplicationLogger.exception(f"Unhandled server error: {exc}")
        body = {
            "status": "error",
            "message": "Something went wrong on the server.",
            "data": None,
            "errors": None,
        }
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    message = "Request failed."
    errors = response.data

    if isinstance(errors, dict) and "detail" in errors:
        message = str(errors["detail"])
        errors = None

    if isinstance(exc, Throttled):
        message = "Too many requests. Please try again later."
        errors = {"retry_after_seconds": int(exc.wait or 0)}

    if response.status_code >= 500:
        ApplicationLogger.error(f"Server error: status={response.status_code}, error={exc}")

    response.data = {
        "status": "error",
        "message": message,
        "data": None,
        "errors": errors,
    }
    return response