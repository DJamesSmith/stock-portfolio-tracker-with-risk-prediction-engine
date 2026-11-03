from django.urls import path
from ..views import views

app_name = "dashboards"

urlpatterns = [
    path("portfolios/", views.portfolio_list_view, name="portfolio-list"),
    path("portfolios/<int:portfolio_id>/", views.portfolio_detail_view, name="portfolio-detail"),
    path("holdings/<int:holding_id>/", views.holding_detail_view, name="holding-detail"),
]