from django.utils import timezone

from config.application_logger import ApplicationLogger
from core.cache import get_from_cache, portfolio_risk_summary_key, save_to_cache
from portfolios.services import get_price_map, get_total_value


def get_average(values):
    if not values:
        return None

    return round(sum(values) / len(values), 4)


def build_risk_summary(portfolio):
    holdings = list(portfolio.holdings.all())
    prices = get_price_map(holdings)

    risk_distribution = {"low": 0, "medium": 0, "high": 0, "not_rated": 0}
    direction_distribution = {"up": 0, "down": 0, "not_predicted": 0}
    risk_scores = []
    forecast_confidences = []

    for holding in holdings:
        risk_distribution[holding.risk_label or "not_rated"] += 1
        direction_distribution[holding.predicted_direction or "not_predicted"] += 1

        if holding.risk_score is not None:
            risk_scores.append(holding.risk_score)

        if holding.prediction_confidence is not None:
            forecast_confidences.append(holding.prediction_confidence)

    return {
        "portfolio_id": portfolio.id,
        "portfolio_name": portfolio.name,
        "holdings_count": len(holdings),
        "total_value": get_total_value(holdings, prices),
        "risk_distribution": risk_distribution,
        "direction_distribution": direction_distribution,
        "average_confidence": get_average(risk_scores),
        "average_forecast_confidence": get_average(forecast_confidences),
        "generated_at": timezone.now(),
    }


def get_risk_summary(portfolio, serializer_class):
    cache_key = portfolio_risk_summary_key(portfolio.id)
    cached_summary = get_from_cache(cache_key)

    if cached_summary is not None:
        ApplicationLogger.info(f"Risk summary cache hit: portfolio_id={portfolio.id}")
        return cached_summary, True

    summary = dict(serializer_class(build_risk_summary(portfolio)).data)
    save_to_cache(cache_key, summary)
    ApplicationLogger.info(f"Risk summary cached: portfolio_id={portfolio.id}")
    return summary, False