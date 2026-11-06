from django.urls import path

from ..views import views

app_name = "market_data"

urlpatterns = [
    path("datasets/", views.dataset_list_view, name="dataset-list"),
    path("datasets/<int:upload_id>/", views.dataset_detail_view, name="dataset-detail"),
    path("datasets/fetch-latest/", views.fetch_latest_prices_view, name="fetch-latest"),
]