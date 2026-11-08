from celery import shared_task

from core.application_logger import ApplicationLogger
from monitoring.services import publish_prediction_update
from portfolios.models import Holding
from .services.predict import recompute_holdings


@shared_task(name="analytics.tasks.recompute_holding_risk")
def recompute_holding_risk():
    return recompute_holdings(Holding.objects.all(), ["risk"])


@shared_task(name="analytics.tasks.recompute_holding_forecast")
def recompute_holding_forecast():
    return recompute_holdings(Holding.objects.all(), ["forecast"])


@shared_task(bind=True, name="analytics.tasks.recompute_single_holding")
def recompute_single_holding(self, holding_id):
    holdings = Holding.objects.filter(id=holding_id)

    if not holdings.exists():
        ApplicationLogger.warning(f"Recompute skipped, holding not found: holding_id={holding_id}")
        return {"holding_id": holding_id, "found": False}

    result = recompute_holdings(holdings, ["risk", "forecast"])
    result["holding_id"] = holding_id
    result["found"] = True
    publish_prediction_update(holding_id, self.request.id)
    return result