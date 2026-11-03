from django.conf import settings
from django.core.cache import cache

from config.application_logger import ApplicationLogger


def portfolio_summary_key(portfolio_id):
    return f"portfolio:{portfolio_id}:summary"


def portfolio_risk_summary_key(portfolio_id):
    return f"portfolio:{portfolio_id}:risk_summary"


def blacklisted_refresh_token_key(jti):
    return f"blacklisted_refresh:{jti}"


def save_to_cache(key, value):
    cache.set(key, value, timeout=settings.CACHE_TTL_SECONDS)


def get_from_cache(key):
    return cache.get(key)


def invalidate_portfolio_cache(portfolio_id):
    cache.delete(portfolio_summary_key(portfolio_id))
    cache.delete(portfolio_risk_summary_key(portfolio_id))
    ApplicationLogger.info(f"Portfolio cache cleared: portfolio_id={portfolio_id}")
