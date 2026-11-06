from django.contrib import admin

from .models import TrainingRun


@admin.register(TrainingRun)
class TrainingRunAdmin(admin.ModelAdmin):
    list_display = ["id", "model_choice", "status", "triggered_by", "risk_version", "forecast_version", "created_at", "finished_at"]
    list_filter = ["status", "model_choice"]
    readonly_fields = ["result", "error", "task_id", "started_at", "finished_at"]