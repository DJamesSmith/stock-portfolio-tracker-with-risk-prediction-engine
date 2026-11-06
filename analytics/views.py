from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.application_logger import ApplicationLogger
from core.responses import api_response
from core.permissions import IsAnalystOrAdminRole
from portfolios.selectors import find_holding, find_portfolio
from portfolios.services import get_price_map
from stock_risk_engine.celery import app as celery_app
from .serializers import HoldingForecastSerializer, HoldingRiskSerializer, RiskSummarySerializer, TaskStatusSerializer
from .services.risk_summary import get_risk_summary
from .tasks import recompute_single_holding


def holding_not_found():
    return api_response("Holding not found.", status_code=status.HTTP_404_NOT_FOUND)


def portfolio_not_found():
    return api_response("Portfolio not found.", status_code=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def holding_risk_api(request, holding_id):
    holding = find_holding(request.user, holding_id)

    if holding is None:
        return holding_not_found()

    context = {"prices": get_price_map([holding])}
    data = HoldingRiskSerializer(holding, context=context).data

    if holding.risk_label is None:
        return api_response("This holding does not have a risk prediction yet.", data=data)

    return api_response("Holding risk retrieved.", data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def holding_forecast_api(request, holding_id):
    holding = find_holding(request.user, holding_id)

    if holding is None:
        return holding_not_found()

    data = HoldingForecastSerializer(holding).data

    if holding.predicted_direction is None:
        return api_response("This holding does not have a forecast yet.", data=data)

    return api_response("Holding forecast retrieved.", data=data)


@api_view(["POST"])
@permission_classes([IsAnalystOrAdminRole])
def holding_recompute_api(request, holding_id):
    holding = find_holding(request.user, holding_id)

    if holding is None:
        return holding_not_found()

    try:
        task = recompute_single_holding.delay(holding.id)
    except Exception as error:
        ApplicationLogger.error(f"Could not queue recompute: holding_id={holding.id}, error={error}")
        return api_response(
            "The background worker is not available. Please try again later.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    ApplicationLogger.info(
        f"Holding recompute queued: holding_id={holding.id}, task_id={task.id}, user={request.user.username}"
    )
    return api_response(
        f"Recomputation for holding {holding.id} has been queued.",
        data={"holding_id": holding.id, "task_id": task.id},
        status_code=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_risk_summary_api(request, portfolio_id):
    portfolio = find_portfolio(request.user, portfolio_id)

    if portfolio is None:
        return portfolio_not_found()

    summary, from_cache = get_risk_summary(portfolio, RiskSummarySerializer)
    data = dict(summary)
    data["from_cache"] = from_cache
    return api_response("Portfolio risk summary retrieved.", data=data)


@api_view(["GET"])
@permission_classes([IsAnalystOrAdminRole])
def task_status_api(request, task_id):
    task = celery_app.AsyncResult(str(task_id))

    result = None
    error = None

    if task.successful():
        result = task.result

    if task.failed():
        error = str(task.result)

    data = TaskStatusSerializer({
        "task_id": task.id,
        "state": task.state,
        "ready": task.ready(),
        "result": result,
        "error": error,
    }).data
    return api_response("Task status retrieved.", data=data)