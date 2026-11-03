from celery import shared_task

from config.application_logger import ApplicationLogger
from portfolios.models import Holding
from .services.predict import recompute_holdings
from .training.train_forecast import train_forecast_model
from .training.train_risk import train_risk_model


@shared_task(name="analytics.tasks.recompute_holding_risk")
def recompute_holding_risk():
    return recompute_holdings(Holding.objects.all(), ["risk"])


@shared_task(name="analytics.tasks.recompute_holding_forecast")
def recompute_holding_forecast():
    return recompute_holdings(Holding.objects.all(), ["forecast"])


@shared_task(name="analytics.tasks.recompute_single_holding")
def recompute_single_holding(holding_id):
    holdings = Holding.objects.filter(id=holding_id)

    if not holdings.exists():
        ApplicationLogger.warning(f"Recompute skipped, holding not found: holding_id={holding_id}")
        return {"holding_id": holding_id, "found": False}

    result = recompute_holdings(holdings, ["risk", "forecast"])
    result["holding_id"] = holding_id
    result["found"] = True
    return result


@shared_task(name="analytics.tasks.retrain_models")
def retrain_models():
    risk_metadata = train_risk_model()
    forecast_metadata = train_forecast_model()

    ApplicationLogger.info(
        f"Models retrained: risk={risk_metadata['model_version']}, forecast={forecast_metadata['model_version']}"
    )
    return {
        "risk": {
            "model_version": risk_metadata["model_version"],
            "comparison": risk_metadata["comparison"]["note"],
        },
        "forecast": {
            "model_version": forecast_metadata["model_version"],
            "comparison": forecast_metadata["comparison"]["note"],
        },
    }