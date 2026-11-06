from decimal import Decimal
import pandas as pd

from core.application_logger import ApplicationLogger
from core.cache import invalidate_admin_dashboard
from portfolios.cache import clear_summary_cache_for_ticker
from ..models import PriceHistory

PRICE_COLUMNS = ["open_price", "high_price", "low_price", "close_price"]
REQUIRED_COLUMNS = ["date"] + PRICE_COLUMNS


def clean_price_frame(frame):
    frame = frame.copy()

    if "volume" not in frame.columns:
        frame["volume"] = None

    frame["date"] = pd.to_datetime(frame["date"].astype(str).str[:10], format="%Y-%m-%d", errors="coerce")

    for column in PRICE_COLUMNS + ["volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=REQUIRED_COLUMNS)
    frame = frame[(frame[PRICE_COLUMNS] > 0).all(axis=1)]
    frame = frame[frame["high_price"] >= frame["low_price"]]
    frame = frame[frame["volume"].isna() | (frame["volume"] >= 0)]
    frame = frame.drop_duplicates(subset=["date"])
    frame["date"] = frame["date"].dt.date
    return frame


def to_decimal(value):
    return Decimal(str(round(float(value), 4)))


def to_volume(value):
    if pd.isna(value):
        return None

    return int(value)


def save_price_rows(ticker, frame):
    ticker = ticker.strip().upper()
    clean_frame = clean_price_frame(frame)

    rows = []
    for row in clean_frame.itertuples(index=False):
        rows.append(PriceHistory(
            ticker=ticker,
            date=row.date,
            open_price=to_decimal(row.open_price),
            high_price=to_decimal(row.high_price),
            low_price=to_decimal(row.low_price),
            close_price=to_decimal(row.close_price),
            volume=to_volume(row.volume),
        ))

    count_before = PriceHistory.objects.filter(ticker=ticker).count()
    PriceHistory.objects.bulk_create(rows, batch_size=5000, ignore_conflicts=True)
    count_after = PriceHistory.objects.filter(ticker=ticker).count()

    inserted = count_after - count_before
    skipped = len(frame) - inserted
    ApplicationLogger.info(f"Price rows saved: ticker={ticker}, inserted={inserted}, skipped={skipped}")

    if inserted > 0:
        clear_summary_cache_for_ticker(ticker)
        invalidate_admin_dashboard()

    return inserted, skipped