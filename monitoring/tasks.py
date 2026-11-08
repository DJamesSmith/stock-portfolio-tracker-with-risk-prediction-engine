from celery import shared_task
from django.utils import timezone

from core.application_logger import ApplicationLogger
from market_data.services.provider import fetch_live_quote
from portfolios.models import Holding
from .services import build_quote, publish_quote


@shared_task(name="monitoring.tasks.poll_live_prices")
def poll_live_prices():
    tickers = sorted(set(Holding.objects.values_list("ticker", flat=True)))
    published_tickers = []
    failed_tickers = []

    for ticker in tickers:
        try:
            price, previous_close = fetch_live_quote(ticker)
        except Exception as error:
            ApplicationLogger.error(f"Live price fetch failed: ticker={ticker}, error={error}")
            failed_tickers.append(ticker)
            continue

        if price is None or previous_close is None:
            ApplicationLogger.warning(f"Live price not available: ticker={ticker}")
            failed_tickers.append(ticker)
            continue

        publish_quote(build_quote(ticker, price, previous_close, timezone.now().date(), "live"))
        published_tickers.append(ticker)

    ApplicationLogger.info(
        f"poll_live_prices finished: checked={len(tickers)}, published={len(published_tickers)}, failed={len(failed_tickers)}"
    )
    return {
        "tickers_checked": len(tickers),
        "tickers_published": published_tickers,
        "tickers_failed": failed_tickers,
    }