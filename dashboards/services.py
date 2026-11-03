from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from analytics.registry import get_latest_version, load_metadata
from config.application_logger import ApplicationLogger
from core.cache import (
    admin_dashboard_key,
    analyst_dashboard_key,
    get_from_cache,
    investor_dashboard_key,
    save_dashboard_to_cache)
from market_data.selectors import latest_price, price_history, tracked_tickers
from portfolios.models import Holding, Portfolio
from portfolios.selectors import visible_holdings, visible_portfolios, with_holdings
from portfolios.services import get_current_price, get_holding_value, get_percent, get_price_map
from .selectors import (
    assigned_investors,
    count_risk_labels,
    count_risk_labels_by_investor,
    count_users_by_role,
    empty_risk_counts,
    market_data_status)
from .serializers import AdminDashboardSerializer, AnalystDashboardSerializer, InvestorDashboardSerializer

HIGH_RISK_LIMIT = 50
DEFAULT_TREND_DAYS = 180


def money_totals(holdings, prices):
    total_cost = Decimal("0")
    current_value = Decimal("0")

    for holding in holdings:
        total_cost += holding.quantity * holding.buy_price
        current_value += get_holding_value(holding, prices)

    gain_loss = current_value - total_cost

    return {
        "total_cost": total_cost,
        "current_value": current_value,
        "gain_loss": gain_loss,
        "gain_loss_percent": get_percent(gain_loss, total_cost),
    }


def build_investor_dashboard(user):
    portfolios = list(with_holdings(visible_portfolios(user)))
    holdings = []

    for portfolio in portfolios:
        holdings.extend(portfolio.holdings.all())

    prices = get_price_map(holdings)

    portfolio_rows = []
    for portfolio in portfolios:
        row = {"id": portfolio.id, "name": portfolio.name, "holdings_count": portfolio.holdings_count}
        row.update(money_totals(portfolio.holdings.all(), prices))
        portfolio_rows.append(row)

    dashboard = {
        "user": user,
        "portfolio_count": len(portfolios),
        "holding_count": len(holdings),
        "risk_distribution": count_risk_labels(visible_holdings(user)),
        "portfolios": portfolio_rows,
        "generated_at": timezone.now(),
    }
    dashboard.update(money_totals(holdings, prices))
    return dashboard


def build_high_risk_row(holding, prices):
    return {
        "holding_id": holding.id,
        "ticker": holding.ticker,
        "portfolio_id": holding.portfolio_id,
        "portfolio_name": holding.portfolio.name,
        "investor": holding.portfolio.user,
        "quantity": holding.quantity,
        "current_price": get_current_price(holding, prices),
        "current_value": get_holding_value(holding, prices),
        "risk_score": holding.risk_score,
        "predicted_direction": holding.predicted_direction,
        "prediction_confidence": holding.prediction_confidence,
        "last_predicted_at": holding.last_predicted_at,
    }


def get_high_risk_holdings(holdings, prices):
    high_risk = []

    for holding in holdings:
        if holding.risk_label == Holding.RiskLabel.HIGH:
            high_risk.append(holding)

    high_risk.sort(key=lambda holding: holding.risk_score or 0, reverse=True)
    rows = [build_high_risk_row(holding, prices) for holding in high_risk[:HIGH_RISK_LIMIT]]
    return len(high_risk), rows


def build_analyst_dashboard(analyst):
    investors = list(assigned_investors(analyst))
    holdings_queryset = visible_holdings(analyst)
    holdings = list(holdings_queryset)
    prices = get_price_map(holdings)
    risk_by_investor = count_risk_labels_by_investor(holdings_queryset)

    holdings_by_investor = {}
    for holding in holdings:
        investor_id = holding.portfolio.user_id
        holdings_by_investor.setdefault(investor_id, []).append(holding)

    client_rows = []
    for investor in investors:
        investor_holdings = holdings_by_investor.get(investor.id, [])
        row = {
            "id": investor.id,
            "username": investor.username,
            "email": investor.email,
            "portfolio_count": investor.portfolio_count,
            "holding_count": len(investor_holdings),
            "risk_distribution": risk_by_investor.get(investor.id, empty_risk_counts()),
        }
        row.update(money_totals(investor_holdings, prices))
        client_rows.append(row)

    high_risk_count, high_risk_rows = get_high_risk_holdings(holdings, prices)

    dashboard = {
        "analyst": analyst,
        "client_count": len(investors),
        "portfolio_count": sum(investor.portfolio_count for investor in investors),
        "holding_count": len(holdings),
        "risk_distribution": count_risk_labels(holdings_queryset),
        "clients": client_rows,
        "high_risk_count": high_risk_count,
        "high_risk_holdings": high_risk_rows,
        "generated_at": timezone.now(),
    }
    dashboard.update(money_totals(holdings, prices))
    return dashboard


def get_model_info(model_type):
    version = get_latest_version(model_type)

    if version is None:
        return None

    try:
        metadata = load_metadata(model_type, version)
    except FileNotFoundError:
        ApplicationLogger.warning(f"Model metadata missing: model_type={model_type}, version={version}")
        return None

    metrics = metadata.get("metrics", {})

    return {
        "version": version,
        "algorithm": metadata.get("algorithm"),
        "trained_at": metadata.get("trained_at"),
        "tickers_count": metadata.get("tickers_count"),
        "validation_metrics": metrics.get("validation"),
        "test_metrics": metrics.get("test"),
        "comparison": metadata.get("comparison", {}).get("note"),
    }


def build_admin_dashboard():
    return {
        "users": count_users_by_role(),
        "portfolio_count": Portfolio.objects.count(),
        "holding_count": Holding.objects.count(),
        "tickers_tracked": len(tracked_tickers()),
        "market_data": market_data_status(),
        "models": {
            "risk": get_model_info("risk"),
            "forecast": get_model_info("forecast"),
        },
        "risk_distribution": count_risk_labels(Holding.objects.all()),
        "generated_at": timezone.now(),
    }


def get_dashboard(cache_key, build_dashboard, serializer_class, *args):
    cached_dashboard = get_from_cache(cache_key)

    if cached_dashboard is not None:
        ApplicationLogger.info(f"Dashboard cache hit: key={cache_key}")
        return cached_dashboard, True

    dashboard = dict(serializer_class(build_dashboard(*args)).data)
    save_dashboard_to_cache(cache_key, dashboard)
    ApplicationLogger.info(f"Dashboard cached: key={cache_key}")
    return dashboard, False


def get_investor_dashboard(user):
    return get_dashboard(investor_dashboard_key(user.id), build_investor_dashboard, InvestorDashboardSerializer, user)


def get_analyst_dashboard(analyst):
    return get_dashboard(analyst_dashboard_key(analyst.id), build_analyst_dashboard, AnalystDashboardSerializer, analyst)


def get_admin_dashboard():
    return get_dashboard(admin_dashboard_key(), build_admin_dashboard, AdminDashboardSerializer)


def get_trend_dates(ticker, start, end):
    if end is None:
        newest_row = latest_price(ticker)
        end = newest_row.date if newest_row else timezone.localdate()

    if start is None:
        start = end - timedelta(days=DEFAULT_TREND_DAYS)

    return start, end


def build_ticker_trend(holding, start=None, end=None):
    start, end = get_trend_dates(holding.ticker, start, end)
    rows = price_history(holding.ticker, start, end).order_by("date").values("date", "close_price")
    points = list(rows)

    return {
        "holding_id": holding.id,
        "ticker": holding.ticker,
        "buy_price": holding.buy_price,
        "buy_date": holding.buy_date,
        "start": start,
        "end": end,
        "points_count": len(points),
        "points": points,
    }


def build_holding_position(holding, prices):
    current_price = get_current_price(holding, prices)
    cost = holding.quantity * holding.buy_price

    if current_price is None:
        return {"current_price": None, "cost": cost, "current_value": None, "gain_loss": None, "gain_loss_percent": None}

    current_value = holding.quantity * current_price
    gain_loss = current_value - cost

    return {
        "current_price": current_price,
        "cost": cost,
        "current_value": current_value,
        "gain_loss": gain_loss,
        "gain_loss_percent": get_percent(gain_loss, cost),
    }