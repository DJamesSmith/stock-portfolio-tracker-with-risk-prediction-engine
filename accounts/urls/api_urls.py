from django.urls import path

from ..views import api_views

app_name = "api_accounts"

urlpatterns = [
    path("register/", api_views.register_api, name="register"),
    path("login/", api_views.login_api, name="login"),
    path("token/refresh/", api_views.refresh_token_api, name="token-refresh"),
    path("logout/", api_views.logout_api, name="logout"),
    path("me/", api_views.me_api, name="me"),
    path("change-password/", api_views.change_password_api, name="change-password"),
    path("users/", api_views.user_list_api, name="user-list"),
    path("users/<int:user_id>/", api_views.user_update_api, name="user-update"),
]
