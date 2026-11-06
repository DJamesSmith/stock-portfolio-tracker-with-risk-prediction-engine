from django.utils import timezone

from analytics.services.predict import recompute_holdings
from core.application_logger import ApplicationLogger
from core.cache import invalidate_admin_dashboard
from market_data.models import PriceHistory
from portfolios.models import Holding
from .dataset import TRAIN_END, VALIDATION_END
from .models import TrainingRun
from .registry import MODEL_PREFIXES, get_latest_version, list_versions, load_metadata
from .train_forecast import train_forecast_model
from .train_risk import train_risk_model

MODEL_TYPE_NAMES = {
    "risk": "Risk model",
    "forecast": "Forecast model",
}
RISK_METRICS = ["accuracy", "macro_f1"]
FORECAST_METRICS = ["accuracy", "f1", "roc_auc"]
METRIC_LABELS = {"accuracy": "Accuracy", "macro_f1": "Macro F1", "f1": "F1", "roc_auc": "ROC-AUC"}


def set_step(run, step):
    run.current_step = step
    run.save(update_fields=["current_step"])


def summarize_risk(metadata):
    forest = metadata["metrics"]["test"]
    baseline = metadata["baseline"]["metrics"]["test"]

    return {
        "version": metadata["model_version"],
        "random_forest": {"accuracy": forest["accuracy"], "macro_f1": forest["macro_f1"]},
        "logistic_regression": {"accuracy": baseline["accuracy"], "macro_f1": baseline["macro_f1"]},
        "beats_baseline": metadata["comparison"]["beats_baseline"],
        "note": metadata["comparison"]["note"],
    }


def summarize_forecast(metadata):
    model = metadata["metrics"]["test"]
    always_up = metadata["baselines"]["always_up"]["test"]
    previous_day = metadata["baselines"]["previous_day_direction"]["test"]

    return {
        "version": metadata["model_version"],
        "gradient_boosting": {"accuracy": model["accuracy"], "f1": model["f1"], "roc_auc": model["roc_auc"]},
        "always_up": {"accuracy": always_up["accuracy"], "f1": always_up["f1"], "roc_auc": always_up["roc_auc"]},
        "previous_day": {"accuracy": previous_day["accuracy"], "f1": previous_day["f1"], "roc_auc": previous_day["roc_auc"]},
        "beats_baselines": metadata["comparison"]["beats_baselines"],
        "note": metadata["comparison"]["note"],
    }


def train_selected_models(run):
    tickers = run.ticker_list()
    trained_types = []

    if run.trains_risk:
        set_step(run, "Training the risk model (Random Forest and Logistic Regression baseline)")
        metadata = train_risk_model(tickers)
        run.risk_version = metadata["model_version"]
        run.result["risk"] = summarize_risk(metadata)
        run.save(update_fields=["risk_version", "result"])
        trained_types.append("risk")

    if run.trains_forecast:
        set_step(run, "Training the forecast model (Gradient Boosting)")
        metadata = train_forecast_model(tickers)
        run.forecast_version = metadata["model_version"]
        run.result["forecast"] = summarize_forecast(metadata)
        run.save(update_fields=["forecast_version", "result"])
        trained_types.append("forecast")

    if run.update_predictions:
        set_step(run, "Updating holding predictions with the new models")
        prediction = recompute_holdings(Holding.objects.all(), trained_types)
        run.result["predictions"] = {
            "holdings_checked": prediction["holdings_checked"],
            "holdings_updated": prediction["holdings_updated"],
            "holdings_skipped": len(prediction["holdings_skipped"]),
        }


def run_training(run):
    if run.status != TrainingRun.Status.PENDING:
        ApplicationLogger.warning(f"Training run skipped: run_id={run.id}, status={run.status}")
        return run

    run.status = TrainingRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save()
    ApplicationLogger.info(f"Training run started: run_id={run.id}, model={run.model_choice}, tickers={run.tickers or 'all'}")

    try:
        train_selected_models(run)
    except ValueError as error:
        ApplicationLogger.error(f"Training run failed: run_id={run.id}, error={error}")
        run.status = TrainingRun.Status.FAILED
        run.error = str(error)
    except Exception as error:
        ApplicationLogger.exception(f"Training run crashed: run_id={run.id}")
        run.status = TrainingRun.Status.FAILED
        run.error = f"Unexpected error: {error}"
    else:
        run.status = TrainingRun.Status.COMPLETED

    run.current_step = ""
    run.finished_at = timezone.now()
    run.save()
    invalidate_admin_dashboard()

    ApplicationLogger.info(
        f"Training run finished: run_id={run.id}, status={run.status}, "
        f"risk={run.risk_version or '-'}, forecast={run.forecast_version or '-'}"
    )
    return run


def cancel_run(run):
    if run.status != TrainingRun.Status.PENDING:
        return False

    run.status = TrainingRun.Status.FAILED
    run.error = "Cancelled by an administrator before it started."
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error", "finished_at"])
    ApplicationLogger.info(f"Training run cancelled: run_id={run.id}")
    return True


def get_data_readiness():
    rows = PriceHistory.objects.all()
    checks = [
        {
            "name": "Training data",
            "description": f"Prices on or before {TRAIN_END:%d %b %Y}",
            "ok": rows.filter(date__lte=TRAIN_END.date()).exists(),
        },
        {
            "name": "Validation data",
            "description": f"Prices during {VALIDATION_END:%Y}",
            "ok": rows.filter(date__gt=TRAIN_END.date(), date__lte=VALIDATION_END.date()).exists(),
        },
        {
            "name": "Test data",
            "description": f"Prices after {VALIDATION_END:%d %b %Y}",
            "ok": rows.filter(date__gt=VALIDATION_END.date()).exists(),
        },
    ]
    return {"checks": checks, "ready": all(check["ok"] for check in checks)}


def get_beats_baseline(metadata):
    comparison = metadata.get("comparison", {})

    if "beats_baseline" in comparison:
        return comparison["beats_baseline"]

    return comparison.get("beats_baselines")


def build_version_row(model_type, version, latest_version):
    try:
        metadata = load_metadata(model_type, version)
    except FileNotFoundError:
        metadata = {}

    test_metrics = metadata.get("metrics", {}).get("test", {})

    if model_type == "risk":
        second_metric = ("Macro F1", test_metrics.get("macro_f1"))
    else:
        second_metric = ("ROC-AUC", test_metrics.get("roc_auc"))

    return {
        "model_type": model_type,
        "type_name": MODEL_TYPE_NAMES[model_type],
        "version": version,
        "algorithm": metadata.get("algorithm", "-"),
        "trained_at": metadata.get("trained_at"),
        "tickers_count": metadata.get("tickers_count"),
        "test_accuracy": test_metrics.get("accuracy"),
        "second_metric_name": second_metric[0],
        "second_metric": second_metric[1],
        "beats_baseline": get_beats_baseline(metadata),
        "is_latest": version == latest_version,
    }


def list_model_versions(model_type=None):
    rows = []

    for current_type in MODEL_PREFIXES:
        if model_type and current_type != model_type:
            continue

        latest_version = get_latest_version(current_type)

        for version in reversed(list_versions(current_type)):
            rows.append(build_version_row(current_type, version, latest_version))

    return rows


def get_models_in_use():
    models = {}

    for model_type in MODEL_PREFIXES:
        latest_version = get_latest_version(model_type)

        if latest_version is None:
            models[model_type] = None
        else:
            models[model_type] = build_version_row(model_type, latest_version, latest_version)

    return models


def build_metric_rows(rows, metric_names):
    table = []

    for name, metrics in rows:
        values = []

        for split_name in ["validation", "test"]:
            for metric_name in metric_names:
                values.append(metrics.get(split_name, {}).get(metric_name))

        table.append({"name": name, "values": values})

    return table


def build_comparison_table(model_type, metadata):
    if model_type == "risk":
        rows = [
            ("Random Forest (this model)", metadata["metrics"]),
            ("Logistic Regression (baseline)", metadata["baseline"]["metrics"]),
        ]
        return RISK_METRICS, build_metric_rows(rows, RISK_METRICS)

    rows = [
        ("Gradient Boosting (this model)", metadata["metrics"]),
        ("Always up (baseline)", metadata["baselines"]["always_up"]),
        ("Same as today (baseline)", metadata["baselines"]["previous_day_direction"]),
    ]
    return FORECAST_METRICS, build_metric_rows(rows, FORECAST_METRICS)


def build_feature_importances(metadata):
    importances = metadata.get("feature_importances") or {}

    if not importances:
        return []

    largest = max(importances.values()) or 1
    rows = []

    for name, value in importances.items():
        rows.append({"name": name, "value": value, "percent": round(value * 100 / largest, 1)})

    return rows


def build_confusion_matrix(metadata):
    matrix = metadata.get("metrics", {}).get("test", {}).get("confusion_matrix")

    if not matrix:
        return None

    rows = []
    for label, counts in zip(matrix["labels"], matrix["rows_are_actual"]):
        rows.append({"actual": label, "counts": counts})

    return {"labels": matrix["labels"], "rows": rows}


def build_per_class(metadata):
    per_class = metadata.get("metrics", {}).get("test", {}).get("per_class")

    if not per_class:
        return []

    return [{"label": label, **scores} for label, scores in per_class.items()]


def build_model_details(model_type, version):
    if model_type not in MODEL_PREFIXES or version not in list_versions(model_type):
        return None

    metadata = load_metadata(model_type, version)
    metric_names, comparison_rows = build_comparison_table(model_type, metadata)
    windows = metadata["training_window"]

    return {
        "model_type": model_type,
        "type_name": MODEL_TYPE_NAMES[model_type],
        "version": version,
        "is_latest": version == get_latest_version(model_type),
        "metadata": metadata,
        "splits": [
            {"name": "Train", **windows["train"]},
            {"name": "Validation", **windows["validation"]},
            {"name": "Test", **windows["test"]},
        ],
        "metric_names": metric_names,
        "metric_labels": [METRIC_LABELS[name] for name in metric_names],
        "comparison_rows": comparison_rows,
        "beats_baseline": get_beats_baseline(metadata),
        "feature_importances": build_feature_importances(metadata),
        "confusion_matrix": build_confusion_matrix(metadata),
        "per_class": build_per_class(metadata),
        "parameters": sorted(metadata.get("parameters", {}).items()),
    }