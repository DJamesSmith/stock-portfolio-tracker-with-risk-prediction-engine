from datetime import timedelta

import pandas as pd
from django.utils import timezone

from core.application_logger import ApplicationLogger
from core.decorators import log_execution_time
from core.cache import invalidate_portfolios_cache
from market_data.models import PriceHistory
from market_data.selectors import latest_price
from portfolios.models import Holding
from ml_training.feature_engineering import build_ticker_features
from ml_training.registry import load_model
from monitoring.services import publish_risk_changes

PRICE_LOOKBACK_DAYS = 400
BULK_UPDATE_BATCH_SIZE = 500

OUTPUT_FIELDS = {
    "risk": ["risk_label", "risk_score", "risk_model_version"],
    "forecast": ["predicted_direction", "prediction_confidence", "forecast_model_version"],
}


def load_recent_prices(ticker):
    newest_row = latest_price(ticker)

    if newest_row is None:
        return None

    start_date = newest_row.date - timedelta(days=PRICE_LOOKBACK_DAYS)
    rows = PriceHistory.objects.filter(ticker=ticker, date__gte=start_date).order_by("date")
    rows = rows.values_list("ticker", "date", "close_price", "volume")

    prices = pd.DataFrame(list(rows), columns=["ticker", "date", "close", "volume"])
    prices["date"] = pd.to_datetime(prices["date"])
    prices["close"] = prices["close"].astype(float)
    prices["volume"] = pd.to_numeric(prices["volume"], errors="coerce")
    return prices


def build_latest_feature_row(ticker, feature_columns):
    prices = load_recent_prices(ticker)

    if prices is None:
        return None, "no price history"

    features = build_ticker_features(prices)
    latest_row = features.iloc[[-1]][feature_columns].astype(float)

    if latest_row.isna().any(axis=None):
        return None, f"not enough price history ({len(prices)} rows)"

    return latest_row, ""


def predict_one(model, feature_row):
    probabilities = model.predict_proba(feature_row)[0]
    best_index = probabilities.argmax()
    label = str(model.classes_[best_index])
    confidence = round(float(probabilities[best_index]), 4)
    return label, confidence


def load_models(model_types):
    models = {}

    for model_type in model_types:
        model, metadata = load_model(model_type)
        models[model_type] = {
            "model": model,
            "version": metadata["model_version"],
            "features": metadata["features"],
        }

    return models


def get_feature_columns(models):
    feature_columns = []

    for loaded in models.values():
        for column in loaded["features"]:
            if column not in feature_columns:
                feature_columns.append(column)

    return feature_columns


def build_feature_rows(holdings, feature_columns):
    feature_rows = {}
    reasons = {}

    for ticker in sorted({holding.ticker for holding in holdings}):
        feature_row, reason = build_latest_feature_row(ticker, feature_columns)
        feature_rows[ticker] = feature_row
        reasons[ticker] = reason

    return feature_rows, reasons


def apply_predictions(holding, feature_row, models, predicted_at):
    if "risk" in models:
        risk = models["risk"]
        holding.risk_label, holding.risk_score = predict_one(risk["model"], feature_row[risk["features"]])
        holding.risk_model_version = risk["version"]

    if "forecast" in models:
        forecast = models["forecast"]
        holding.predicted_direction, holding.prediction_confidence = predict_one(
            forecast["model"], feature_row[forecast["features"]]
        )
        holding.forecast_model_version = forecast["version"]

    holding.last_predicted_at = predicted_at


def get_update_fields(model_types):
    fields = []

    for model_type in model_types:
        fields.extend(OUTPUT_FIELDS[model_type])

    fields.append("last_predicted_at")
    return fields


@log_execution_time
def recompute_holdings(holdings, model_types):
    holdings = list(holdings)
    models = load_models(model_types)
    feature_rows, reasons = build_feature_rows(holdings, get_feature_columns(models))
    predicted_at = timezone.now()

    updated_holdings = []
    skipped_holdings = []
    risk_changes = {}

    for holding in holdings:
        feature_row = feature_rows.get(holding.ticker)

        if feature_row is None:
            reason = reasons[holding.ticker]
            ApplicationLogger.warning(f"Prediction skipped: holding_id={holding.id}, ticker={holding.ticker}, reason={reason}")
            skipped_holdings.append({"holding_id": holding.id, "ticker": holding.ticker, "reason": reason})
            continue

        previous_label = holding.risk_label
        apply_predictions(holding, feature_row, models, predicted_at)
        updated_holdings.append(holding)

        if "risk" in models and holding.risk_label != previous_label:
            risk_changes[holding.id] = previous_label

    if updated_holdings:
        Holding.objects.bulk_update(updated_holdings, get_update_fields(model_types), batch_size=BULK_UPDATE_BATCH_SIZE)

    invalidate_portfolios_cache({holding.portfolio_id for holding in updated_holdings})
    publish_risk_changes(risk_changes)

    model_versions = {model_type: loaded["version"] for model_type, loaded in models.items()}
    ApplicationLogger.info(
        f"Predictions finished: models={model_types}, checked={len(holdings)}, "
        f"updated={len(updated_holdings)}, skipped={len(skipped_holdings)}, versions={model_versions}"
    )
    return {
        "models": model_versions,
        "holdings_checked": len(holdings),
        "holdings_updated": len(updated_holdings),
        "holdings_skipped": skipped_holdings,
        "risk_changes": len(risk_changes),
    }