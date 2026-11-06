from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.application_logger import ApplicationLogger
from core.decorators import admin_required
from core.responses import get_form_errors
from ..forms import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_FILE_MB, DatasetUploadForm
from ..models import DatasetUpload
from ..selectors import price_data_summary, tracked_tickers
from ..services.dataset_upload import create_dataset_upload, delete_upload_files
from ..tasks import fetch_daily_prices, import_dataset_upload_task

UPLOADS_PER_PAGE = 10


def queue_dataset_import(upload):
    try:
        task = import_dataset_upload_task.delay(upload.id)
    except Exception as error:
        ApplicationLogger.error(f"Could not queue dataset import: upload_id={upload.id}, error={error}")
        upload.status = DatasetUpload.Status.FAILED
        upload.error = "Could not reach the task queue. Start Redis and a Celery worker, then upload the files again."
        upload.save(update_fields=["status", "error"])
        delete_upload_files(upload)
        return False

    DatasetUpload.objects.filter(id=upload.id).update(task_id=task.id)
    return True


def render_dataset_list(request, errors=None, form_data=None, status=200):
    uploads = DatasetUpload.objects.select_related("uploaded_by")
    page = Paginator(uploads, UPLOADS_PER_PAGE).get_page(request.GET.get("page"))

    context = {
        "uploads": page,
        "has_active_upload": any(upload.is_active for upload in page),
        "summary": price_data_summary(),
        "seed_ticker_count": len(tracked_tickers()),
        "allowed_extensions": ", ".join(ALLOWED_UPLOAD_EXTENSIONS),
        "max_file_mb": MAX_UPLOAD_FILE_MB,
        "errors": errors,
        "form_data": form_data or {},
    }
    return render(request, "market_data/dataset_list.html", context, status=status)


@admin_required
def dataset_list_view(request):
    if request.method != "POST":
        ApplicationLogger.info(f"Dataset page requested: username={request.user.username}")
        return render_dataset_list(request)

    form = DatasetUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        ApplicationLogger.warning(f"Dataset upload validation failed: username={request.user.username}")
        return render_dataset_list(request, errors=get_form_errors(form), form_data={"tickers": request.POST.get("tickers", "")}, status=400)

    upload = create_dataset_upload(form, request.user)

    if queue_dataset_import(upload):
        messages.success(request, f"Upload received ({upload.name}). The import is running in the background.")
    else:
        messages.error(request, "The files were received but the import could not be started. Is the Celery worker running?")

    return redirect("market_data:dataset-detail", upload_id=upload.id)


@admin_required
def dataset_detail_view(request, upload_id):
    upload = get_object_or_404(DatasetUpload.objects.select_related("uploaded_by"), id=upload_id)
    results = upload.results

    context = {
        "upload": upload,
        "loaded_results": sorted([result for result in results if result["status"] == "loaded"], key=lambda result: result["ticker"]),
        "problem_results": [result for result in results if result["status"] != "loaded"],
    }
    return render(request, "market_data/dataset_detail.html", context)


@admin_required
@require_POST
def fetch_latest_prices_view(request):
    try:
        task = fetch_daily_prices.delay()
    except Exception as error:
        ApplicationLogger.error(f"Could not queue fetch_daily_prices: error={error}")
        messages.error(request, "Could not reach the task queue. Start Redis and a Celery worker first.")
        return redirect("market_data:dataset-list")

    ApplicationLogger.info(f"Latest price fetch queued from template: username={request.user.username}, task_id={task.id}")
    messages.success(request, "Fetching the latest daily prices for every tracked ticker in the background. Check the admin dashboard in a few minutes.")
    return redirect("market_data:dataset-list")