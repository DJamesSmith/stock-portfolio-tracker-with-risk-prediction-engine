from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls.urls")),

    # APIs
    path("api/accounts/", include("accounts.urls.api_urls")),
    path("api/market/", include("market_data.urls")),
]