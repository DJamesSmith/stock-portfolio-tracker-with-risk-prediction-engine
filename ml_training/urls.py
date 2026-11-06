from django.urls import path
from . import views

app_name = "ml_training"

urlpatterns = [
    path("", views.training_view, name="training"),
    path("runs/<int:run_id>/", views.run_detail_view, name="run-detail"),
    path("runs/<int:run_id>/cancel/", views.cancel_run_view, name="run-cancel"),
    path("models/", views.model_list_view, name="model-list"),
    path("models/<str:model_type>/<str:version>/", views.model_detail_view, name="model-detail"),
]