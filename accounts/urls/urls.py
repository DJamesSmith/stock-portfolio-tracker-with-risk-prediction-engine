from django.urls import path
from ..views import views

app_name = "accounts"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/password/", views.change_password_view, name="change-password"),
    path("users/", views.user_list_view, name="user-list"),
    path("users/<int:user_id>/update/", views.user_role_update_view, name="user-role-update"),
]