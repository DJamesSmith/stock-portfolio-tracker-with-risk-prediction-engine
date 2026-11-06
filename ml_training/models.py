from datetime import timedelta

from django.db import models
from django.utils import timezone

STALE_RUN_HOURS = 6


class TrainingRun(models.Model):
    class ModelChoice(models.TextChoices):
        ALL = "all", "Both models"
        RISK = "risk", "Risk model only"
        FORECAST = "forecast", "Forecast model only"

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for worker"
        RUNNING = "running", "Training"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    model_choice = models.CharField(max_length=20, choices=ModelChoice.choices, default=ModelChoice.ALL)
    tickers = models.CharField(max_length=500, blank=True, help_text="Optional comma-separated tickers. Leave empty to train on every ticker.")
    update_predictions = models.BooleanField(default=True, help_text="Recompute every holding's prediction with the new models when training finishes.")
    triggered_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="training_runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_step = models.CharField(max_length=255, blank=True)
    task_id = models.CharField(max_length=255, blank=True)
    risk_version = models.CharField(max_length=100, blank=True)
    forecast_version = models.CharField(max_length=100, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "training_runs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Training run {self.id}: {self.model_choice} ({self.status})"

    @property
    def is_active(self):
        return self.status in [self.Status.PENDING, self.Status.RUNNING]

    @property
    def trains_risk(self):
        return self.model_choice in [self.ModelChoice.ALL, self.ModelChoice.RISK]

    @property
    def trains_forecast(self):
        return self.model_choice in [self.ModelChoice.ALL, self.ModelChoice.FORECAST]

    @property
    def duration(self):
        if not self.started_at:
            return None

        end = self.finished_at or timezone.now()
        return end - self.started_at

    def ticker_list(self):
        return [ticker.strip().upper() for ticker in self.tickers.split(",") if ticker.strip()]

    @classmethod
    def active_runs(cls):
        stale_time = timezone.now() - timedelta(hours=STALE_RUN_HOURS)
        return cls.objects.filter(status__in=[cls.Status.PENDING, cls.Status.RUNNING], created_at__gte=stale_time)