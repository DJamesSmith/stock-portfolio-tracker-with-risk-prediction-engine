import shutil
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd
from django.conf import settings
from django.utils import timezone

from core.application_logger import ApplicationLogger
from core.decorators import log_execution_time
from ..forms import TickerForm
from ..models import DatasetUpload
from .ingestion import REQUIRED_COLUMNS, save_price_rows

CSV_COLUMNS = {
    "date": "date",
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "volume": "volume",
}
MAX_ZIP_MEMBER_MB = 200


def get_upload_folder(upload):
    return Path(settings.MEDIA_ROOT) / "dataset_uploads" / str(upload.id)


def delete_upload_files(upload):
    shutil.rmtree(get_upload_folder(upload), ignore_errors=True)


def describe_files(files):
    first_name = Path(files[0].name).name

    if len(files) == 1:
        return first_name

    return f"{first_name} and {len(files) - 1} more files"


def store_uploaded_files(upload, files):
    folder = get_upload_folder(upload)

    for index, uploaded_file in enumerate(files):
        file_folder = folder / str(index)
        file_folder.mkdir(parents=True, exist_ok=True)

        with open(file_folder / Path(uploaded_file.name).name, "wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)


def create_dataset_upload(form, user):
    files = form.cleaned_data["files"]
    upload = form.save(commit=False)
    upload.uploaded_by = user
    upload.name = describe_files(files)[:255]
    upload.save()

    store_uploaded_files(upload, files)
    ApplicationLogger.info(f"Dataset upload stored: upload_id={upload.id}, files={len(files)}, username={user.username}")
    return upload


def is_csv_name(name):
    return name.lower().endswith(".csv") and not name.startswith(".")


def list_stored_files(folder):
    return sorted(path for path in folder.glob("*/*") if path.is_file())


def list_zip_members(archive):
    members = []

    for member in archive.infolist():
        name = PurePosixPath(member.filename).name

        if member.is_dir() or "__MACOSX" in member.filename or not is_csv_name(name):
            continue

        members.append(member)

    return members


def count_price_files(folder):
    total = 0

    for path in list_stored_files(folder):
        if path.suffix.lower() != ".zip":
            total += 1
            continue

        try:
            with zipfile.ZipFile(path) as archive:
                total += len(list_zip_members(archive))
        except zipfile.BadZipFile:
            total += 1

    return total


def new_result(file_name, ticker=""):
    return {"file": file_name, "ticker": ticker, "status": "skipped", "inserted": 0, "skipped": 0, "message": ""}


def read_price_csv(file_object):
    frame = pd.read_csv(file_object)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    return frame.rename(columns=CSV_COLUMNS)


def load_price_file(file_name, file_object, wanted_tickers):
    result = new_result(file_name)
    ticker_form = TickerForm({"ticker": Path(file_name).stem})

    if not ticker_form.is_valid():
        result["message"] = "File name is not a valid ticker, for example AAPL.csv."
        return result

    ticker = ticker_form.cleaned_data["ticker"]
    result["ticker"] = ticker

    if wanted_tickers and ticker not in wanted_tickers:
        return None

    try:
        frame = read_price_csv(file_object)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
        ApplicationLogger.warning(f"Could not read CSV: file={file_name}, error={error}")
        result["status"] = "failed"
        result["message"] = "Could not read the CSV file."
        return result

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]

    if missing_columns:
        result["status"] = "failed"
        result["message"] = f"Missing columns: {', '.join(missing_columns)}."
        return result

    inserted, skipped = save_price_rows(ticker, frame)
    result["status"] = "loaded"
    result["inserted"] = inserted
    result["skipped"] = skipped

    if "volume" not in frame.columns:
        result["message"] = "No Volume column. Volume was left empty."

    return result


def record_result(upload, result):
    upload.files_processed += 1

    if result is not None:
        upload.results.append(result)

        if result["status"] == "loaded":
            upload.rows_inserted += result["inserted"]
            upload.rows_skipped += result["skipped"]

    upload.save(update_fields=["files_processed", "results", "rows_inserted", "rows_skipped"])


def import_zip_file(upload, path, wanted_tickers):
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        result = new_result(path.name)
        result["status"] = "failed"
        result["message"] = "Not a valid zip file."
        record_result(upload, result)
        return

    with archive:
        for member in list_zip_members(archive):
            name = PurePosixPath(member.filename).name

            if member.file_size > MAX_ZIP_MEMBER_MB * 1024 * 1024:
                result = new_result(name)
                result["status"] = "failed"
                result["message"] = f"File is larger than {MAX_ZIP_MEMBER_MB} MB."
                record_result(upload, result)
                continue

            with archive.open(member) as file_object:
                record_result(upload, load_price_file(name, file_object, wanted_tickers))


def import_stored_files(upload, wanted_tickers):
    for path in list_stored_files(get_upload_folder(upload)):
        if path.suffix.lower() == ".zip":
            import_zip_file(upload, path, wanted_tickers)
            continue

        with open(path, "rb") as file_object:
            record_result(upload, load_price_file(path.name, file_object, wanted_tickers))


def add_missing_ticker_results(upload, wanted_tickers):
    found_tickers = {result["ticker"] for result in upload.results}

    for ticker in wanted_tickers:
        if ticker not in found_tickers:
            result = new_result("-", ticker)
            result["message"] = "No CSV file was found for this ticker."
            upload.results.append(result)


def finish_upload(upload):
    loaded_tickers = {result["ticker"] for result in upload.results if result["status"] == "loaded"}
    upload.tickers_loaded = len(loaded_tickers)

    if upload.status == DatasetUpload.Status.PROCESSING and not loaded_tickers:
        upload.status = DatasetUpload.Status.FAILED
        upload.error = "No price files were loaded. Check that each file is named after its ticker and has Date, Open, High, Low and Close columns."
    elif upload.status == DatasetUpload.Status.PROCESSING:
        upload.status = DatasetUpload.Status.COMPLETED

    upload.finished_at = timezone.now()
    upload.save()
    delete_upload_files(upload)


@log_execution_time
def import_dataset_upload(upload):
    if upload.status != DatasetUpload.Status.PENDING:
        ApplicationLogger.warning(f"Dataset import skipped: upload_id={upload.id}, status={upload.status}")
        return upload

    wanted_tickers = upload.ticker_list()
    upload.status = DatasetUpload.Status.PROCESSING
    upload.started_at = timezone.now()
    upload.total_files = count_price_files(get_upload_folder(upload))
    upload.save()

    try:
        import_stored_files(upload, wanted_tickers)
        add_missing_ticker_results(upload, wanted_tickers)
    except Exception as error:
        ApplicationLogger.exception(f"Dataset import failed: upload_id={upload.id}")
        upload.status = DatasetUpload.Status.FAILED
        upload.error = f"The import stopped because of an unexpected error: {error}"
    finally:
        finish_upload(upload)

    ApplicationLogger.info(
        f"Dataset import finished: upload_id={upload.id}, status={upload.status}, "
        f"tickers={upload.tickers_loaded}, inserted={upload.rows_inserted}, skipped={upload.rows_skipped}"
    )
    return upload
