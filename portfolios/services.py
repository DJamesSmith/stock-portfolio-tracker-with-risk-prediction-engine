from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from config.application_logger import ApplicationLogger
from core.cache import get_from_cache, portfolio_summary_key, save_to_cache
from market_data.selectors import latest_price, latest_prices
from market_data.tasks import refresh_single_ticker

RECENT_PRICE_DAYS = 7


def get_price_map(holdings):
    tickers = set()

    for holding in holdings:
        tickers.add(holding.ticker)

    if not tickers:
        return {}

    return latest_prices(tickers)


def get_current_price(holding, prices):
    price_row = prices.get(holding.ticker)

    if price_row is None:
        return None

    return price_row.close_price


def get_holding_value(holding, prices):
    current_price = get_current_price(holding, prices)

    if current_price is None:
        current_price = holding.buy_price

    return holding.quantity * current_price


def get_total_value(holdings, prices):
    total = Decimal("0")

    for holding in holdings:
        total += get_holding_value(holding, prices)

    return total


def get_percent(part, whole):
    if whole == 0:
        return Decimal("0")

    return part / whole * 100


def build_portfolio_summary(portfolio):
    holdings = list(portfolio.holdings.all())
    prices = get_price_map(holdings)

    total_cost = Decimal("0")
    current_value = Decimal("0")
    risk_distribution = {"low": 0, "medium": 0, "high": 0, "not_rated": 0}
    holding_rows = []

    for holding in holdings:
        price_row = prices.get(holding.ticker)
        cost = holding.quantity * holding.buy_price
        value = get_holding_value(holding, prices)
        gain_loss = value - cost

        total_cost += cost
        current_value += value
        risk_distribution[holding.risk_label or "not_rated"] += 1

        holding_rows.append({
            "id": holding.id,
            "ticker": holding.ticker,
            "quantity": holding.quantity,
            "buy_price": holding.buy_price,
            "current_price": price_row.close_price if price_row else None,
            "price_date": price_row.date if price_row else None,
            "cost": cost,
            "current_value": value,
            "gain_loss": gain_loss,
            "gain_loss_percent": get_percent(gain_loss, cost),
            "risk_label": holding.risk_label,
        })

    total_gain_loss = current_value - total_cost

    return {
        "portfolio_id": portfolio.id,
        "portfolio_name": portfolio.name,
        "owner": portfolio.user,
        "holdings_count": len(holdings),
        "total_cost": total_cost,
        "current_value": current_value,
        "unrealised_gain_loss": total_gain_loss,
        "unrealised_gain_loss_percent": get_percent(total_gain_loss, total_cost),
        "risk_distribution": risk_distribution,
        "holdings": holding_rows,
        "generated_at": timezone.now(),
    }


def get_portfolio_summary(portfolio, serializer_class):
    cache_key = portfolio_summary_key(portfolio.id)
    cached_summary = get_from_cache(cache_key)

    if cached_summary is not None:
        ApplicationLogger.info(f"Portfolio summary cache hit: portfolio_id={portfolio.id}")
        return cached_summary, True

    summary = serializer_class(build_portfolio_summary(portfolio)).data
    summary = dict(summary)
    save_to_cache(cache_key, summary)
    ApplicationLogger.info(f"Portfolio summary cached: portfolio_id={portfolio.id}")
    return summary, False


def needs_price_refresh(ticker):
    price_row = latest_price(ticker)

    if price_row is None:
        return True

    oldest_allowed_date = timezone.localdate() - timedelta(days=RECENT_PRICE_DAYS)
    return price_row.date < oldest_allowed_date


def queue_price_refresh(ticker):
    try:
        task = refresh_single_ticker.delay(ticker)
    except Exception as error:
        ApplicationLogger.error(f"Could not queue price refresh: ticker={ticker}, error={error}")
        return None

    ApplicationLogger.info(f"Price refresh queued for new holding: ticker={ticker}, task_id={task.id}")
    return task.id