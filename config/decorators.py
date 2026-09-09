from functools import wraps
from time import perf_counter
from .application_logger import ApplicationLogger


def log_execution_time(view_func):
    """
    Logs how long a function takes to execute.

    This decorator is intentionally generic so it can later be placed
    on Random Forest / Gradient Boosting training functions in ml_engine.
    """

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