from functools import wraps
from time import perf_counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .application_logger import ApplicationLogger


def log_execution_time(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        ApplicationLogger.info(f"Started execution: {view_func.__module__}.{view_func.__name__}")

        try:
            result = view_func(*args, **kwargs)
            return result
        except Exception:
            ApplicationLogger.exception(f"Execution failed: {view_func.__module__}.{view_func.__name__}")
            raise
        finally:
            execution_time = perf_counter() - start_time
            ApplicationLogger.info(f"Finished execution: {view_func.__module__}.{view_func.__name__} in {execution_time:.4f} seconds")
    return wrapper


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.role != "admin":
            ApplicationLogger.warning(f"Admin page denied: username={request.user.username}, path={request.path}")
            messages.error(request, "Only administrators can open that page.")
            return redirect("accounts:dashboard")

        return view_func(request, *args, **kwargs)
    return wrapper