import pandas as pd

from market_data.models import PriceHistory
from ..feature_engineering import FEATURE_COLUMNS, build_features

TRAIN_END = pd.Timestamp("2022-12-31")
VALIDATION_END = pd.Timestamp("2023-12-31")


def load_prices(tickers=None):
    rows = PriceHistory.objects.order_by("ticker", "date")

    if tickers:
        rows = rows.filter(ticker__in=tickers)

    rows = rows.values_list("ticker", "date", "close_price", "volume")
    prices = pd.DataFrame(list(rows.iterator(chunk_size=20000)), columns=["ticker", "date", "close", "volume"])

    prices["date"] = pd.to_datetime(prices["date"])
    prices["close"] = prices["close"].astype(float)
    prices["volume"] = pd.to_numeric(prices["volume"], errors="coerce")
    return prices


def load_feature_rows(tickers=None):
    prices = load_prices(tickers)

    if prices.empty and tickers:
        raise ValueError(f"No PriceHistory rows found for: {', '.join(tickers)}")

    if prices.empty:
        raise ValueError("No rows found in PriceHistory. Run load_price_history first.")

    features = build_features(prices)
    return features.dropna(subset=FEATURE_COLUMNS)


def split_by_date(rows, gap_days=0):
    gap = pd.Timedelta(days=gap_days)

    train = rows[rows["date"] <= TRAIN_END - gap]
    validation = rows[(rows["date"] > TRAIN_END) & (rows["date"] <= VALIDATION_END - gap)]
    test = rows[rows["date"] > VALIDATION_END]

    for name, part in [("training", train), ("validation", validation), ("test", test)]:
        if part.empty:
            raise ValueError(f"The {name} split is empty. Check that PriceHistory covers 2015 to 2025.")

    return train, validation, test


def date_range(rows):
    return {
        "start": rows["date"].min().date().isoformat(),
        "end": rows["date"].max().date().isoformat(),
        "rows": len(rows),
    }


def round_number(value):
    return round(float(value), 4)