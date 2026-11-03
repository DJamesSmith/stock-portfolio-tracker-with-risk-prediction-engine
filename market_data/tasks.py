from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from config.application_logger import ApplicationLogger
from .selectors import latest_price, tracked_tickers
from .services.ingestion import save_price_rows
from .services.provider import fetch_prices

NEW_TICKER_HISTORY_DAYS = 3650
MAX_REFRESH_RETRIES = 3


def get_start_date(ticker):
    latest_row = latest_price(ticker)

    if latest_row is None:
        return timezone.localdate() - timedelta(days=NEW_TICKER_HISTORY_DAYS)

    return latest_row.date + timedelta(days=1)


def ingest_ticker(ticker):
    start_date = get_start_date(ticker)

    if start_date > timezone.localdate():
        ApplicationLogger.info(f"Prices already up to date: ticker={ticker}")
        return 0

    frame = fetch_prices(ticker, start_date)
    inserted, skipped = save_price_rows(ticker, frame)
    return inserted


@shared_task(name="market_data.tasks.fetch_daily_prices")
def fetch_daily_prices():
    tickers = tracked_tickers()
    updated_tickers = []
    failed_tickers = []

    for ticker in tickers:
        try:
            inserted = ingest_ticker(ticker)
        except Exception as error:
            ApplicationLogger.error(f"Daily price fetch failed: ticker={ticker}, error={error}")
            failed_tickers.append(ticker)
            continue

        if inserted > 0:
            updated_tickers.append(ticker)

    ApplicationLogger.info(
        f"fetch_daily_prices finished: checked={len(tickers)}, updated={len(updated_tickers)}, failed={len(failed_tickers)}"
    )
    return {
        "tickers_checked": len(tickers),
        "tickers_updated": updated_tickers,
        "tickers_failed": failed_tickers,
    }


@shared_task(bind=True, name="market_data.tasks.refresh_single_ticker", max_retries=MAX_REFRESH_RETRIES)
def refresh_single_ticker(self, ticker):
    ticker = ticker.strip().upper()

    try:
        inserted = ingest_ticker(ticker)
    except Exception as error:
        wait_seconds = 60 * (2 ** self.request.retries)
        ApplicationLogger.error(
            f"Ticker refresh failed: ticker={ticker}, attempt={self.request.retries + 1}, "
            f"retry_in={wait_seconds}s, error={error}"
        )
        raise self.retry(exc=error, countdown=wait_seconds)

    ApplicationLogger.info(f"Ticker refreshed: ticker={ticker}, rows_inserted={inserted}")
    return {"ticker": ticker, "rows_inserted": inserted}
