from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin, IsAnalyst, IsInvestor
from config.application_logger import ApplicationLogger
from config.responses import api_response, get_form_errors
from market_data.forms import PriceHistoryFilterForm
from portfolios.selectors import find_holding
from ..serializers import TickerTrendSerializer
from ..services import build_ticker_trend, get_admin_dashboard, get_analyst_dashboard, get_investor_dashboard


def dashboard_response(message, dashboard, from_cache):
    data = dict(dashboard)
    data["from_cache"] = from_cache
    return api_response(message, data=data)


@api_view(["GET"])
@permission_classes([IsInvestor])
def investor_dashboard_api(request):
    dashboard, from_cache = get_investor_dashboard(request.user)
    ApplicationLogger.info(f"Investor dashboard served: user={request.user.username}, from_cache={from_cache}")
    return dashboard_response("Investor dashboard retrieved.", dashboard, from_cache)


@api_view(["GET"])
@permission_classes([IsAnalyst])
def analyst_dashboard_api(request):
    dashboard, from_cache = get_analyst_dashboard(request.user)
    ApplicationLogger.info(f"Analyst dashboard served: user={request.user.username}, from_cache={from_cache}")
    return dashboard_response("Analyst dashboard retrieved.", dashboard, from_cache)


@api_view(["GET"])
@permission_classes([IsAdmin])
def admin_dashboard_api(request):
    dashboard, from_cache = get_admin_dashboard()
    ApplicationLogger.info(f"Admin dashboard served: user={request.user.username}, from_cache={from_cache}")
    return dashboard_response("Admin dashboard retrieved.", dashboard, from_cache)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def holding_trend_api(request, holding_id):
    holding = find_holding(request.user, holding_id)

    if holding is None:
        return api_response("Holding not found.", status_code=status.HTTP_404_NOT_FOUND)

    filter_form = PriceHistoryFilterForm(request.query_params)

    if not filter_form.is_valid():
        return api_response(
            "Invalid date range.",
            errors=get_form_errors(filter_form),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    trend = build_ticker_trend(holding, filter_form.cleaned_data["start"], filter_form.cleaned_data["end"])
    data = TickerTrendSerializer(trend).data

    if trend["points_count"] == 0:
        return api_response(f"No price data found for {holding.ticker} in this date range.", data=data)

    return api_response("Ticker trend retrieved.", data=data)
