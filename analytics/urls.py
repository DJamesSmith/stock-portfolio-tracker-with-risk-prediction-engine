from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("holdings/<int:holding_id>/risk/", views.holding_risk_api, name="holding-risk"),
    path("holdings/<int:holding_id>/forecast/", views.holding_forecast_api, name="holding-forecast"),
    path("holdings/<int:holding_id>/recompute/", views.holding_recompute_api, name="holding-recompute"),
    path("portfolio/<int:portfolio_id>/risk-summary/", views.portfolio_risk_summary_api, name="portfolio-risk-summary"),
    path("tasks/<uuid:task_id>/", views.task_status_api, name="task-status"),
]