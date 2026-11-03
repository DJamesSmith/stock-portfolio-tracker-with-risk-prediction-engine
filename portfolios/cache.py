from core.cache import invalidate_portfolios_cache
from .models import Holding


def clear_summary_cache_for_ticker(ticker):
    portfolio_ids = Holding.objects.filter(ticker=ticker.upper()).values_list("portfolio_id", flat=True).distinct()
    invalidate_portfolios_cache(portfolio_ids)