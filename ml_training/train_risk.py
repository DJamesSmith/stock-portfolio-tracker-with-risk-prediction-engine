from django.utils import timezone
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from core.decorators import log_execution_time
from .algorithms import build_logistic_regression, build_random_forest
from .feature_engineering import FEATURE_COLUMNS
from .labels import RISK_HORIZON_DAYS, RISK_LABELS, add_future_volatility, add_risk_labels, get_risk_thresholds
from .registry import save_model
from .dataset import date_range, load_feature_rows, round_number, split_by_date

LABEL_GAP_DAYS = 45


def evaluate(model, rows):
    predicted = model.predict(rows[FEATURE_COLUMNS])
    actual = rows["risk_label"]
    report = classification_report(actual, predicted, labels=RISK_LABELS, output_dict=True, zero_division=0)

    per_class = {}
    for label in RISK_LABELS:
        per_class[label] = {
            "precision": round_number(report[label]["precision"]),
            "recall": round_number(report[label]["recall"]),
            "f1": round_number(report[label]["f1-score"]),
            "support": int(report[label]["support"]),
        }

    return {
        "accuracy": round_number(report["accuracy"]),
        "macro_f1": round_number(f1_score(actual, predicted, labels=RISK_LABELS, average="macro")),
        "per_class": per_class,
        "confusion_matrix": {
            "labels": RISK_LABELS,
            "rows_are_actual": confusion_matrix(actual, predicted, labels=RISK_LABELS).tolist(),
        },
    }


def get_feature_importances(model):
    importances = {}

    for name, value in zip(FEATURE_COLUMNS, model.feature_importances_):
        importances[name] = round_number(value)

    return dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))


def compare_models(forest_metrics, baseline_metrics):
    forest_f1 = forest_metrics["macro_f1"]
    baseline_f1 = baseline_metrics["macro_f1"]
    beats_baseline = forest_f1 > baseline_f1

    if beats_baseline:
        note = f"Random Forest beat Logistic Regression on test macro F1 ({forest_f1} vs {baseline_f1})."
    else:
        note = f"Random Forest did NOT beat Logistic Regression on test macro F1 ({forest_f1} vs {baseline_f1})."

    return {"metric": "test macro_f1", "beats_baseline": beats_baseline, "note": note}


@log_execution_time
def train_risk_model(tickers=None):
    rows = load_feature_rows(tickers)
    rows = add_future_volatility(rows)
    rows = rows.dropna(subset=["future_volatility"])

    train, validation, test = split_by_date(rows, gap_days=LABEL_GAP_DAYS)
    thresholds = get_risk_thresholds(train["future_volatility"])

    train = add_risk_labels(train, thresholds)
    validation = add_risk_labels(validation, thresholds)
    test = add_risk_labels(test, thresholds)

    forest = build_random_forest()
    forest.fit(train[FEATURE_COLUMNS], train["risk_label"])

    baseline = build_logistic_regression()
    baseline.fit(train[FEATURE_COLUMNS], train["risk_label"])

    forest_metrics = {"validation": evaluate(forest, validation), "test": evaluate(forest, test)}
    baseline_metrics = {"validation": evaluate(baseline, validation), "test": evaluate(baseline, test)}

    metadata = {
        "model_type": "risk",
        "algorithm": "RandomForestClassifier",
        "trained_at": timezone.now().isoformat(),
        "tickers_count": int(rows["ticker"].nunique()),
        "training_window": {
            "train": date_range(train),
            "validation": date_range(validation),
            "test": date_range(test),
            "label_gap_days": LABEL_GAP_DAYS,
        },
        "features": FEATURE_COLUMNS,
        "label": {
            "name": "risk_label",
            "classes": RISK_LABELS,
            "source": f"standard deviation of daily returns over the next {RISK_HORIZON_DAYS} trading days",
            "thresholds": {
                "low_max": round(thresholds["low_max"], 6),
                "medium_max": round(thresholds["medium_max"], 6),
            },
        },
        "parameters": forest.get_params(),
        "metrics": forest_metrics,
        "feature_importances": get_feature_importances(forest),
        "baseline": {
            "algorithm": "LogisticRegression (StandardScaler)",
            "metrics": baseline_metrics,
        },
        "comparison": compare_models(forest_metrics["test"], baseline_metrics["test"]),
    }

    save_model("risk", forest, metadata)
    return metadata