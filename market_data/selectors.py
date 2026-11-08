from django.conf import settings
from django.db.models import Count, Max, Min

from .models import PriceHistory


def latest_price(ticker):
    return PriceHistory.objects.filter(ticker=ticker.upper()).order_by("-date").first()


def latest_prices(tickers):
    tickers = {ticker.upper() for ticker in tickers}
    rows = PriceHistory.objects.filter(ticker__in=tickers).order_by("ticker", "-date").distinct("ticker")
    return {row.ticker: row for row in rows}


def price_history(ticker, start=None, end=None):
    rows = PriceHistory.objects.filter(ticker=ticker.upper())

    if start:
        rows = rows.filter(date__gte=start)

    if end:
        rows = rows.filter(date__lte=end)

    return rows.order_by("-date")


def tracked_tickers():
    stored_tickers = set(PriceHistory.objects.values_list("ticker", flat=True).distinct())
    seed_tickers = set(settings.MARKET_SEED_TICKERS)
    return sorted(stored_tickers | seed_tickers)

def price_data_summary():
    summary = PriceHistory.objects.aggregate(
        rows=Count("id"),
        tickers=Count("ticker", distinct=True),
        first_date=Min("date"),
        last_date=Max("date"))
    return summary