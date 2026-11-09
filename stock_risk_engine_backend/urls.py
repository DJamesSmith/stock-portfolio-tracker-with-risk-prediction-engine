from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls.urls")),
    path("", include("dashboards.urls.urls")),
    path("", include("market_data.urls.urls")),
    path("ml/", include("ml_training.urls")),

    # APIs
    path("api/accounts/", include("accounts.urls.api_urls")),
    path("api/market/", include("market_data.urls.api_urls")),
    path("api/", include("portfolios.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/dashboard/", include("dashboards.urls.api_urls")),
]