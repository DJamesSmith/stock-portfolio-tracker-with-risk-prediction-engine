from core.cache import invalidate_portfolio_cache
from .models import Holding


def clear_summary_cache_for_ticker(ticker):
    portfolio_ids = Holding.objects.filter(ticker=ticker.upper()).values_list("portfolio_id", flat=True).distinct()

    for portfolio_id in portfolio_ids:
        invalidate_portfolio_cache(portfolio_id)