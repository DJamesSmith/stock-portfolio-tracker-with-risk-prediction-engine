from django.urls import path
from .views.views import (
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    RegisterView,
    UserListView,
    UserRoleUpdateView,
)
from .views.api_views import (
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    RegisterView,
    UserListView,
    UserRoleUpdateView,
)

app_name = "api_accounts"

urlpatterns = [
    # templates
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:user_id>/", UserRoleUpdateView.as_view(), name="user-role-update"),


    # APIs
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:user_id>/", UserRoleUpdateView.as_view(), name="user-role-update"),
]