import pandas as pd

RISK_HORIZON_DAYS = 30
RISK_LABELS = ["low", "medium", "high"]
DIRECTION_LABELS = ["down", "up"]


def add_future_volatility(features):
    frames = []

    for ticker, ticker_rows in features.groupby("ticker"):
        ticker_rows = ticker_rows.sort_values("date").copy()
        rolling_volatility = ticker_rows["daily_return"].rolling(RISK_HORIZON_DAYS).std()
        ticker_rows["future_volatility"] = rolling_volatility.shift(-RISK_HORIZON_DAYS)
        frames.append(ticker_rows)

    return pd.concat(frames, ignore_index=True)


def get_risk_thresholds(future_volatility):
    return {
        "low_max": float(future_volatility.quantile(1 / 3)),
        "medium_max": float(future_volatility.quantile(2 / 3)),
    }


def get_risk_label(volatility, thresholds):
    if volatility <= thresholds["low_max"]:
        return "low"

    if volatility <= thresholds["medium_max"]:
        return "medium"

    return "high"


def add_risk_labels(rows, thresholds):
    rows = rows.copy()
    rows["risk_label"] = rows["future_volatility"].apply(get_risk_label, thresholds=thresholds)
    return rows


def add_direction_labels(features):
    frames = []

    for ticker, ticker_rows in features.groupby("ticker"):
        ticker_rows = ticker_rows.sort_values("date").copy()
        ticker_rows["next_close"] = ticker_rows["close"].shift(-1)
        frames.append(ticker_rows)

    labelled = pd.concat(frames, ignore_index=True)
    labelled = labelled.dropna(subset=["next_close"])
    labelled["direction"] = "down"
    labelled.loc[labelled["next_close"] > labelled["close"], "direction"] = "up"
    return labelled