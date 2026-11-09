from django.urls import path
from . import api_views

app_name = "analytics"

urlpatterns = [
    path("holdings/<int:holding_id>/risk/", api_views.holding_risk_api, name="holding-risk"),                                   # GET
    path("holdings/<int:holding_id>/forecast/", api_views.holding_forecast_api, name="holding-forecast"),                       # GET
    path("holdings/<int:holding_id>/recompute/", api_views.holding_recompute_api, name="holding-recompute"),                    # Analyst/Admin - POST
    path("portfolio/<int:portfolio_id>/risk-summary/", api_views.portfolio_risk_summary_api, name="portfolio-risk-summary"),    # GET
    path("tasks/<uuid:task_id>/", api_views.task_status_api, name="task-status"),                                               # Analyst/Admin - GET
]