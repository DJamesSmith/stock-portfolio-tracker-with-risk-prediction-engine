from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.application_logger import ApplicationLogger
from core.decorators import admin_required
from core.responses import get_form_errors
from market_data.selectors import price_data_summary
from .forms import TrainingRunForm
from .models import TrainingRun
from .services import build_model_details, cancel_run, get_data_readiness, get_models_in_use, list_model_versions
from .tasks import run_training_task

RUNS_PER_PAGE = 10


def queue_training(run):
    try:
        task = run_training_task.delay(run.id)
    except Exception as error:
        ApplicationLogger.error(f"Could not queue training run: run_id={run.id}, error={error}")
        run.status = TrainingRun.Status.FAILED
        run.error = "Could not reach the task queue. Start Redis and a Celery worker, then try again."
        run.save(update_fields=["status", "error"])
        return False

    TrainingRun.objects.filter(id=run.id).update(task_id=task.id)
    return True


def render_training_page(request, errors=None, form_data=None, status=200):
    runs = TrainingRun.objects.select_related("triggered_by")
    page = Paginator(runs, RUNS_PER_PAGE).get_page(request.GET.get("page"))

    context = {
        "runs": page,
        "has_active_run": TrainingRun.active_runs().exists(),
        "readiness": get_data_readiness(),
        "summary": price_data_summary(),
        "models": get_models_in_use(),
        "model_choices": TrainingRun.ModelChoice.choices,
        "errors": errors,
        "form_data": form_data or {"model_choice": TrainingRun.ModelChoice.ALL, "update_predictions": True},
    }
    return render(request, "ml_training/training.html", context, status=status)


@admin_required
def training_view(request):
    if request.method != "POST":
        ApplicationLogger.info(f"ML training page requested: username={request.user.username}")
        return render_training_page(request)

    form = TrainingRunForm(request.POST)

    if not form.is_valid():
        ApplicationLogger.warning(f"Training form validation failed: username={request.user.username}")
        form_data = {
            "model_choice": request.POST.get("model_choice", ""),
            "tickers": request.POST.get("tickers", ""),
            "update_predictions": request.POST.get("update_predictions") == "on",
        }
        return render_training_page(request, errors=get_form_errors(form), form_data=form_data, status=400)

    run = form.save(commit=False)
    run.triggered_by = request.user
    run.save()
    ApplicationLogger.info(f"Training run created from template: run_id={run.id}, username={request.user.username}")

    if queue_training(run):
        messages.success(request, "Training started in the background. This page refreshes until it finishes.")
    else:
        messages.error(request, "Training could not be started. Is the Celery worker running?")

    return redirect("ml_training:run-detail", run_id=run.id)


@admin_required
def run_detail_view(request, run_id):
    run = get_object_or_404(TrainingRun.objects.select_related("triggered_by"), id=run_id)
    return render(request, "ml_training/run_detail.html", {"run": run})


@admin_required
@require_POST
def cancel_run_view(request, run_id):
    run = get_object_or_404(TrainingRun, id=run_id)

    if cancel_run(run):
        messages.success(request, f"Training run #{run.id} was cancelled.")
    else:
        messages.error(request, "Only runs that are still waiting for a worker can be cancelled.")

    return redirect("ml_training:run-detail", run_id=run.id)


@admin_required
def model_list_view(request):
    model_type = request.GET.get("type", "")
    context = {
        "versions": list_model_versions(model_type or None),
        "selected_type": model_type,
    }
    return render(request, "ml_training/model_list.html", context)


@admin_required
def model_detail_view(request, model_type, version):
    details = build_model_details(model_type, version)

    if details is None:
        raise Http404("Model version not found.")

    return render(request, "ml_training/model_detail.html", {"model": details})