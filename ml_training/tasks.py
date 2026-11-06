from celery import shared_task

from core.application_logger import ApplicationLogger
from market_data.models import PriceHistory
from .models import TrainingRun
from .services import run_training


def build_task_result(run):
    return {
        "run_id": run.id,
        "status": run.status,
        "risk_version": run.risk_version,
        "forecast_version": run.forecast_version,
        "error": run.error,
    }


@shared_task(name="ml_training.tasks.run_training")
def run_training_task(run_id):
    run = TrainingRun.objects.filter(id=run_id).first()

    if run is None:
        ApplicationLogger.warning(f"Training skipped, run not found: run_id={run_id}")
        return {"run_id": run_id, "found": False}

    return build_task_result(run_training(run))


@shared_task(bind=True, name="ml_training.tasks.retrain_models")
def retrain_models(self):
    if TrainingRun.active_runs().exists():
        ApplicationLogger.warning("Scheduled retraining skipped: another training run is active.")
        return {"skipped": True, "reason": "Another training run is active."}

    if not PriceHistory.objects.exists():
        ApplicationLogger.warning("Scheduled retraining skipped: no price history stored.")
        return {"skipped": True, "reason": "No price history stored."}

    run = TrainingRun.objects.create(
        model_choice=TrainingRun.ModelChoice.ALL,
        update_predictions=False,
        task_id=self.request.id or "",
    )
    return build_task_result(run_training(run))