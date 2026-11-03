from django.conf import settings
from django.core.cache import cache

from accounts.models import User
from config.application_logger import ApplicationLogger

DASHBOARD_CACHE_SECONDS = 300


def portfolio_summary_key(portfolio_id):
    return f"portfolio:{portfolio_id}:summary"


def portfolio_risk_summary_key(portfolio_id):
    return f"portfolio:{portfolio_id}:risk_summary"


def blacklisted_refresh_token_key(jti):
    return f"blacklisted_refresh:{jti}"


def investor_dashboard_key(user_id):
    return f"dashboard:investor:{user_id}"


def analyst_dashboard_key(user_id):
    return f"dashboard:analyst:{user_id}"


def admin_dashboard_key():
    return "dashboard:admin"


def save_to_cache(key, value):
    cache.set(key, value, timeout=settings.CACHE_TTL_SECONDS)


def save_dashboard_to_cache(key, value):
    cache.set(key, value, timeout=DASHBOARD_CACHE_SECONDS)


def get_from_cache(key):
    return cache.get(key)


def invalidate_admin_dashboard():
    cache.delete(admin_dashboard_key())


def invalidate_user_dashboards(user_ids):
    keys = [admin_dashboard_key()]

    for user_id in user_ids:
        if user_id is None:
            continue

        keys.append(investor_dashboard_key(user_id))
        keys.append(analyst_dashboard_key(user_id))

    cache.delete_many(keys)


def invalidate_portfolios_cache(portfolio_ids):
    portfolio_ids = set(portfolio_ids)

    if not portfolio_ids:
        return

    keys = []
    for portfolio_id in portfolio_ids:
        keys.append(portfolio_summary_key(portfolio_id))
        keys.append(portfolio_risk_summary_key(portfolio_id))

    cache.delete_many(keys)

    owners = User.objects.filter(portfolios__id__in=portfolio_ids).values_list("id", "assigned_analyst_id").distinct()

    user_ids = set()
    for owner_id, analyst_id in owners:
        user_ids.add(owner_id)
        user_ids.add(analyst_id)

    invalidate_user_dashboards(user_ids)
    ApplicationLogger.info(f"Portfolio cache cleared: portfolio_ids={sorted(portfolio_ids)}")


def invalidate_portfolio_cache(portfolio_id):
    invalidate_portfolios_cache([portfolio_id])