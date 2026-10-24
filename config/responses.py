from rest_framework import status as http
from rest_framework.response import Response


def api_response(message, data=None, errors=None, status_code=http.HTTP_200_OK):
    if status_code < 400:
        result = "success"
    else:
        result = "error"

    body = {
        "status": result,
        "message": message,
        "data": data,
        "errors": errors,
    }
    return Response(body, status=status_code)


def get_form_errors(form):
    errors = {}

    for field, error_list in form.errors.get_json_data().items():
        errors[field] = [error["message"] for error in error_list]

    return errors