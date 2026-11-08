from datetime import datetime, timezone as dt_timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone

from accounts.models import User
from accounts.utils import decode_access_token, get_user_from_token_payload
from core.application_logger import ApplicationLogger
from core.cache import live_quote_key
from market_data.models import PriceHistory
from portfolios.models import Holding

ADMIN_GROUP = "admins"
LIVE_QUOTE_CACHE_SECONDS = 24 * 60 * 60


def to_iso(value):
    if value is None:
        return None

    return value.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp_to_iso(timestamp):
    return to_iso(datetime.fromtimestamp(timestamp, tz=dt_timezone.utc))


def build_event(event_type, message, data=None, errors=None):
    if errors:
        status = "error"
    else:
        status = "success"

    return {
        "type": event_type,
        "status": status,
        "message": message,
        "data": data,
        "errors": errors,
    }


def authenticate_live_token(token):
    if not token:
        return None, None

    payload = decode_access_token(token)

    if payload is None or payload.get("token_type") != "access":
        return None, None

    user = get_user_from_token_payload(payload)

    if user is None:
        return None, None

    return payload, user


def user_group(user_id):
    return f"user_{user_id}"


def ticker_group(ticker):
    return f"ticker_{ticker}"


def groups_for_user(user):
    groups = [user_group(user.id)]

    if user.role == User.Role.ADMIN:
        groups.append(ADMIN_GROUP)

    return groups


def groups_for_holding(holding):
    owner = holding.portfolio.user
    groups = [ADMIN_GROUP]

    if owner.role != User.Role.ADMIN:
        groups.append(user_group(owner.id))

    if owner.assigned_analyst_id:
        groups.append(user_group(owner.assigned_analyst_id))

    return groups


def send_to_groups(groups, event):
    channel_layer = get_channel_layer()

    try:
        for group in groups:
            async_to_sync(channel_layer.group_send)(group, {"type": "live.event", "event": event})
    except Exception as error:
        ApplicationLogger.error(f"Live event not sent: type={event['type']}, error={error}")
        return False

    return True


def holding_data(holding):
    return {
        "holding_id": holding.id,
        "portfolio_id": holding.portfolio_id,
        "portfolio_name": holding.portfolio.name,
        "owner": holding.portfolio.user.username,
        "ticker": holding.ticker,
        "risk_label": holding.risk_label,
        "risk_score": holding.risk_score,
        "risk_model_version": holding.risk_model_version,
        "predicted_direction": holding.predicted_direction,
        "prediction_confidence": holding.prediction_confidence,
        "forecast_model_version": holding.forecast_model_version,
        "last_predicted_at": to_iso(holding.last_predicted_at),
    }


def publish_risk_changes(changes):
    if not changes:
        return 0

    holdings = Holding.objects.filter(id__in=changes.keys()).select_related("portfolio__user")

    for holding in holdings:
        data = holding_data(holding)
        data["previous_label"] = changes[holding.id]
        message = f"{holding.ticker} risk is now {holding.risk_label}."
        send_to_groups(groups_for_holding(holding), build_event("risk.changed", message, data))

    ApplicationLogger.info(f"Risk change alerts sent: holdings={len(changes)}")
    return len(changes)


def publish_prediction_update(holding_id, task_id):
    holding = Holding.objects.filter(id=holding_id).select_related("portfolio__user").first()

    if holding is None:
        return False

    data = holding_data(holding)
    data["task_id"] = task_id
    message = f"Prediction updated for {holding.ticker}."
    return send_to_groups(groups_for_holding(holding), build_event("prediction.updated", message, data))


def build_quote(ticker, price, previous_close, price_date, source):
    change = price - previous_close

    if previous_close:
        change_percent = change / previous_close * 100
    else:
        change_percent = 0

    return {
        "ticker": ticker,
        "price": f"{price:.4f}",
        "previous_close": f"{previous_close:.4f}",
        "change": f"{change:.4f}",
        "change_percent": f"{change_percent:.2f}",
        "date": price_date.isoformat(),
        "as_of": to_iso(timezone.now()),
        "source": source,
    }


def daily_quote(ticker):
    rows = list(PriceHistory.objects.filter(ticker=ticker).order_by("-date")[:2])

    if not rows:
        return None

    latest_row = rows[0]
    previous_row = rows[-1]
    return build_quote(ticker, float(latest_row.close_price), float(previous_row.close_price), latest_row.date, "daily")


def current_quote(ticker):
    quote = cache.get(live_quote_key(ticker))

    if quote is None:
        quote = daily_quote(ticker)

    return quote


def publish_quote(quote):
    cache.set(live_quote_key(quote["ticker"]), quote, timeout=LIVE_QUOTE_CACHE_SECONDS)
    message = f"New price for {quote['ticker']}."
    return send_to_groups([ticker_group(quote["ticker"])], build_event("price.update", message, quote))


def publish_daily_price(ticker):
    quote = daily_quote(ticker)

    if quote is None:
        return False

    return publish_quote(quote)