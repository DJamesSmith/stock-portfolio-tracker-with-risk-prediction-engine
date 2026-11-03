from django.urls import path

from . import views

app_name = "portfolios"

urlpatterns = [
    path("portfolios/", views.portfolio_list_api, name="portfolio-list"),
    path("portfolios/<int:portfolio_id>/", views.portfolio_detail_api, name="portfolio-detail"),
    path("portfolios/<int:portfolio_id>/summary/", views.portfolio_summary_api, name="portfolio-summary"),
    path("portfolios/<int:portfolio_id>/holdings/", views.portfolio_holdings_api, name="portfolio-holdings"),
    path("holdings/<int:holding_id>/", views.holding_detail_api, name="holding-detail"),
]