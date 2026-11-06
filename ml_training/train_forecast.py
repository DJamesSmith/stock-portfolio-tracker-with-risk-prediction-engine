import numpy as np
from django.utils import timezone
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from core.decorators import log_execution_time
from .algorithms import build_gradient_boosting
from .feature_engineering import FEATURE_COLUMNS
from .labels import DIRECTION_LABELS, add_direction_labels
from .registry import save_model
from .dataset import date_range, load_feature_rows, round_number, split_by_date


def score_predictions(actual, predicted, up_probability):
    is_up = actual == "up"

    if is_up.nunique() < 2:
        roc_auc = None
    else:
        roc_auc = round_number(roc_auc_score(is_up, up_probability))

    return {
        "accuracy": round_number(accuracy_score(actual, predicted)),
        "f1": round_number(f1_score(actual, predicted, pos_label="up", zero_division=0)),
        "roc_auc": roc_auc,
        "up_share_actual": round_number(is_up.mean()),
    }


def evaluate_model(model, rows):
    predicted = model.predict(rows[FEATURE_COLUMNS])
    up_column = list(model.classes_).index("up")
    up_probability = model.predict_proba(rows[FEATURE_COLUMNS])[:, up_column]
    return score_predictions(rows["direction"], predicted, up_probability)


def evaluate_always_up(rows):
    predicted = np.full(len(rows), "up")
    up_probability = np.ones(len(rows))
    return score_predictions(rows["direction"], predicted, up_probability)


def evaluate_previous_direction(rows):
    predicted = np.where(rows["daily_return"] > 0, "up", "down")
    up_probability = (rows["daily_return"] > 0).astype(float)
    return score_predictions(rows["direction"], predicted, up_probability)


def compare_with_baselines(model_metrics, always_up_metrics, previous_metrics):
    best_baseline_accuracy = max(always_up_metrics["accuracy"], previous_metrics["accuracy"])
    model_accuracy = model_metrics["accuracy"]
    model_roc_auc = model_metrics["roc_auc"] or 0
    beats_baselines = model_accuracy > best_baseline_accuracy and model_roc_auc > 0.5

    if beats_baselines:
        note = f"Model beat both baselines on test accuracy ({model_accuracy} vs best baseline {best_baseline_accuracy})."
    else:
        note = (
            f"Model did NOT clearly beat the baselines on test data "
            f"(accuracy {model_accuracy} vs best baseline {best_baseline_accuracy}, ROC-AUC {model_metrics['roc_auc']})."
        )

    note += " Around 50-55% accuracy is normal for next-day direction and is not proof of a useful trading model."
    return {"metric": "test accuracy and roc_auc", "beats_baselines": beats_baselines, "note": note}


@log_execution_time
def train_forecast_model(tickers=None):
    rows = load_feature_rows(tickers)
    rows = add_direction_labels(rows)

    train, validation, test = split_by_date(rows)

    model = build_gradient_boosting()
    model.fit(train[FEATURE_COLUMNS], train["direction"])

    model_metrics = {"validation": evaluate_model(model, validation), "test": evaluate_model(model, test)}
    always_up_metrics = {"validation": evaluate_always_up(validation), "test": evaluate_always_up(test)}
    previous_metrics = {"validation": evaluate_previous_direction(validation), "test": evaluate_previous_direction(test)}

    metadata = {
        "model_type": "forecast",
        "algorithm": "HistGradientBoostingClassifier",
        "trained_at": timezone.now().isoformat(),
        "tickers_count": int(rows["ticker"].nunique()),
        "training_window": {
            "train": date_range(train),
            "validation": date_range(validation),
            "test": date_range(test),
        },
        "features": FEATURE_COLUMNS,
        "label": {
            "name": "predicted_direction",
            "classes": DIRECTION_LABELS,
            "source": "up when the next trading day's close is above today's close, otherwise down",
        },
        "parameters": model.get_params(),
        "metrics": model_metrics,
        "baselines": {
            "always_up": always_up_metrics,
            "previous_day_direction": previous_metrics,
        },
        "comparison": compare_with_baselines(model_metrics["test"], always_up_metrics["test"], previous_metrics["test"]),
    }

    save_model("forecast", model, metadata)
    return metadata