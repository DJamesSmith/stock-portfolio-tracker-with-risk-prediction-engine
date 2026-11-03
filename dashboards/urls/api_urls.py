from django.urls import path
from ..views import api_views

app_name = "api_dashboards"

urlpatterns = [
    path("investor/", api_views.investor_dashboard_api, name="investor"),
    path("analyst/", api_views.analyst_dashboard_api, name="analyst"),
    path("admin/", api_views.admin_dashboard_api, name="admin"),
    path("holdings/<int:holding_id>/trend/", api_views.holding_trend_api, name="holding-trend"),
]