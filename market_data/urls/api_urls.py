from django.urls import path

from ..views import api_views as views

app_name = "api_market_data"

urlpatterns = [
    path("prices/<str:ticker>/", views.latest_price_api, name="latest-price"),
    path("prices/<str:ticker>/history/", views.price_history_api, name="price-history"),
    path("refresh/<str:ticker>/", views.refresh_ticker_api, name="refresh"),
]