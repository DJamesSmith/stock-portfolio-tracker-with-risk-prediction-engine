from django.urls import path
from . import api_views

app_name = "portfolios"

urlpatterns = [
    path("portfolios/", api_views.portfolio_list_api, name="portfolio-list"),                                       # GET, POST
    path("portfolios/<int:portfolio_id>/", api_views.portfolio_detail_api, name="portfolio-detail"),                # GET, PATCH, DELETE
    path("portfolios/<int:portfolio_id>/summary/", api_views.portfolio_summary_api, name="portfolio-summary"),      # GET
    path("portfolios/<int:portfolio_id>/holdings/", api_views.portfolio_holdings_api, name="portfolio-holdings"),   # GET POST
    path("holdings/<int:holding_id>/", api_views.holding_detail_api, name="holding-detail"),                        # GET, PATCH, DELETE
]