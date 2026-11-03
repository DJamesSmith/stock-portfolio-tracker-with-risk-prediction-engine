from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated

from config.application_logger import ApplicationLogger
from config.responses import api_response, get_form_errors
from core.pagination import StandardPagination
from core.permissions import IsAnalystOrAdminRole
from core.throttles import MarketRefreshThrottle
from .forms import PriceHistoryFilterForm, TickerForm
from .selectors import latest_price, price_history
from .serializers import PriceHistorySerializer
from .tasks import refresh_single_ticker


def invalid_ticker_response(form):
    return api_response("Invalid ticker.", errors=get_form_errors(form), status_code=status.HTTP_400_BAD_REQUEST)


def no_data_response(ticker):
    return api_response(f"No price data found for {ticker}.", status_code=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_price_api(request, ticker):
    ticker_form = TickerForm({"ticker": ticker})

    if not ticker_form.is_valid():
        return invalid_ticker_response(ticker_form)

    ticker = ticker_form.cleaned_data["ticker"]
    row = latest_price(ticker)

    if row is None:
        return no_data_response(ticker)

    return api_response("Latest price retrieved.", data=PriceHistorySerializer(row).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def price_history_api(request, ticker):
    ticker_form = TickerForm({"ticker": ticker})

    if not ticker_form.is_valid():
        return invalid_ticker_response(ticker_form)

    ticker = ticker_form.cleaned_data["ticker"]
    filter_form = PriceHistoryFilterForm(request.query_params)

    if not filter_form.is_valid():
        return api_response(
            "Invalid date range.",
            errors=get_form_errors(filter_form),
            status_code=status.HTTP_400_BAD_REQUEST)

    if latest_price(ticker) is None:
        return no_data_response(ticker)

    rows = price_history(ticker, filter_form.cleaned_data["start"], filter_form.cleaned_data["end"])

    paginator = StandardPagination()
    page = paginator.paginate_queryset(rows, request)

    data = {
        "count": paginator.page.paginator.count,
        "next": paginator.get_next_link(),
        "previous": paginator.get_previous_link(),
        "results": PriceHistorySerializer(page, many=True).data,
    }
    return api_response("Price history retrieved.", data=data)


@api_view(["POST"])
@permission_classes([IsAnalystOrAdminRole])
@throttle_classes([MarketRefreshThrottle])
def refresh_ticker_api(request, ticker):
    ticker_form = TickerForm({"ticker": ticker})

    if not ticker_form.is_valid():
        return invalid_ticker_response(ticker_form)

    ticker = ticker_form.cleaned_data["ticker"]
    task = refresh_single_ticker.delay(ticker)

    ApplicationLogger.info(f"Ticker refresh queued: ticker={ticker}, task_id={task.id}, user={request.user.username}")
    return api_response(f"Price refresh for {ticker} has been queued.", data={"ticker": ticker, "task_id": task.id}, status_code=status.HTTP_202_ACCEPTED)