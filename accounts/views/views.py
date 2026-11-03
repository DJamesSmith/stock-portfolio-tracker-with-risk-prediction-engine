from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.application_logger import ApplicationLogger
from config.responses import get_form_errors
from core.cache import invalidate_admin_dashboard, invalidate_user_dashboards
from dashboards.services import get_admin_dashboard, get_analyst_dashboard, get_investor_dashboard
from ..forms import (
    AdminUserUpdateForm,
    ChangePasswordForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    build_admin_update_data)
from ..models import User
from ..utils import find_user_by_login

USERS_PER_PAGE = 20


def home_view(request):
    ApplicationLogger.info("Home page requested.")
    return render(request, "accounts/home.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method != "POST":
        ApplicationLogger.info("Registration page requested.")
        return render(request, "accounts/register.html")

    form = RegisterForm(request.POST)

    if form.is_valid():
        user = form.save()
        invalidate_admin_dashboard()
        messages.success(request, "Investor account created successfully. Please log in.")
        ApplicationLogger.info(f"Template registration completed: username={user.username}")
        return redirect("accounts:login")

    ApplicationLogger.warning("Template registration validation failed.")
    context = {
        "errors": get_form_errors(form),
        "form_data": {
            "username": request.POST.get("username", ""),
            "email": request.POST.get("email", ""),
        },
    }
    return render(request, "accounts/register.html", context, status=400)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method != "POST":
        ApplicationLogger.info("Login page requested.")
        return render(request, "accounts/login.html")

    form = LoginForm(request.POST)

    if not form.is_valid():
        context = {"errors": get_form_errors(form)}
        return render(request, "accounts/login.html", context, status=400)

    identifier = form.cleaned_data["username_or_email"]
    user = find_user_by_login(identifier)

    if user is None or not user.check_password(form.cleaned_data["password"]):
        ApplicationLogger.warning(f"Template login failed: identifier={identifier}")
        context = {"errors": {"login": ["Invalid username/email or password."]}}
        return render(request, "accounts/login.html", context, status=401)

    if not user.is_active:
        ApplicationLogger.warning(f"Inactive user attempted template login: username={user.username}")
        context = {"errors": {"login": ["This account is inactive."]}}
        return render(request, "accounts/login.html", context, status=403)

    login(request, user)
    messages.success(request, f"Welcome, {user.username}.")
    ApplicationLogger.info(f"Template login completed: username={user.username}")
    return redirect("accounts:dashboard")


@login_required
@require_POST
def logout_view(request):
    username = request.user.username
    logout(request)
    messages.success(request, "You have been logged out.")
    ApplicationLogger.info(f"Template logout completed: username={username}")
    return redirect("accounts:login")


@login_required
def dashboard_view(request):
    ApplicationLogger.info(f"Dashboard requested: username={request.user.username}")
    role = request.user.role

    if role == User.Role.ADMIN:
        dashboard, from_cache = get_admin_dashboard()
    elif role == User.Role.ANALYST:
        dashboard, from_cache = get_analyst_dashboard(request.user)
    else:
        dashboard, from_cache = get_investor_dashboard(request.user)

    context = {
        "is_investor": role == User.Role.INVESTOR,
        "is_analyst": role == User.Role.ANALYST,
        "is_admin": role == User.Role.ADMIN,
        "dashboard": dashboard,
        "from_cache": from_cache,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def profile_view(request):
    if request.method != "POST":
        ApplicationLogger.info(f"Profile page requested: username={request.user.username}")
        return render(request, "accounts/profile.html")

    form = ProfileForm(request.POST, instance=request.user)

    if form.is_valid():
        user = form.save()
        messages.success(request, "Profile updated successfully.")
        ApplicationLogger.info(f"Template profile updated: username={user.username}")
        return redirect("accounts:profile")

    request.user.refresh_from_db()
    ApplicationLogger.warning(f"Template profile validation failed: username={request.user.username}")
    context = {"errors": get_form_errors(form)}
    return render(request, "accounts/profile.html", context, status=400)


@login_required
def change_password_view(request):
    if request.method != "POST":
        return render(request, "accounts/change_password.html")

    form = ChangePasswordForm(request.user, request.POST)

    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password changed successfully.")
        return redirect("accounts:profile")

    context = {"errors": get_form_errors(form)}
    return render(request, "accounts/change_password.html", context, status=400)


def render_user_list(request, errors=None, status=200):
    users = User.objects.select_related("assigned_analyst").order_by("id")
    context = {
        "users": Paginator(users, USERS_PER_PAGE).get_page(request.GET.get("page")),
        "analysts": User.objects.filter(role=User.Role.ANALYST, is_active=True),
        "roles": User.Role.choices,
        "errors": errors,
    }
    return render(request, "accounts/user_list.html", context, status=status)


@login_required
def user_list_view(request):
    if request.user.role != User.Role.ADMIN:
        ApplicationLogger.warning(f"Unauthorized user management page access: username={request.user.username}")
        messages.error(request, "Only administrators can manage users.")
        return redirect("accounts:dashboard")

    ApplicationLogger.info(f"Admin user list requested: username={request.user.username}")
    return render_user_list(request)


@login_required
@require_POST
def user_role_update_view(request, user_id):
    if request.user.role != User.Role.ADMIN:
        ApplicationLogger.warning(f"Unauthorized user role update attempt: username={request.user.username}")
        messages.error(request, "Only administrators can update users.")
        return redirect("accounts:dashboard")

    user = get_object_or_404(User, id=user_id)

    if user.id == request.user.id:
        ApplicationLogger.warning(f"Admin attempted to change own role: username={request.user.username}")
        messages.error(request, "You cannot change your own role.")
        return redirect("accounts:user-list")

    old_analyst_id = user.assigned_analyst_id
    form = AdminUserUpdateForm(build_admin_update_data(user, request.POST), instance=user)

    if form.is_valid():
        updated_user = form.save()
        invalidate_user_dashboards([updated_user.id, old_analyst_id, updated_user.assigned_analyst_id])
        messages.success(request, f"{updated_user.username} was updated successfully.")
        ApplicationLogger.info(f"Template admin user update completed: admin={request.user.username}, user={updated_user.username}")
        return redirect("accounts:user-list")

    ApplicationLogger.warning(f"Template admin user update failed: admin={request.user.username}, target={user.username}")
    return render_user_list(request, errors=get_form_errors(form), status=400)