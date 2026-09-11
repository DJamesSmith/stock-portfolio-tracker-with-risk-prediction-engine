from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.application_logger import ApplicationLogger

from ..models import User
from ..serializers import (
    AdminUserUpdateSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


def home_view(request):
    ApplicationLogger.info("Home page requested.")

    return render(
        request,
        "accounts/home.html",
    )


def register_view(request):
    if request.method == "GET":
        ApplicationLogger.info("Registration page requested.")

        return render(request, "accounts/register.html")

    serializer = RegisterSerializer(data=request.POST)

    if serializer.is_valid():
        user = serializer.save()

        messages.success(
            request,
            "Investor account created successfully. Please log in.",
        )

        ApplicationLogger.info(
            f"Template registration completed: username={user.username}"
        )

        return redirect("accounts:login")

    form_data = request.POST.dict()

    form_data.pop("password", None)
    form_data.pop("password_confirmation", None)

    ApplicationLogger.warning("Template registration validation failed.")

    return render(
        request,
        "accounts/register.html",
        {
            "errors": serializer.errors,
            "form_data": form_data,
        },
        status=400,
    )


def login_view(request):
    if request.method == "GET":
        ApplicationLogger.info("Login page requested.")

        return render(
            request,
            "accounts/login.html",
        )

    serializer = LoginSerializer(data=request.POST)

    if serializer.is_valid():
        user = serializer.validated_data["user"]

        login(request, user)

        messages.success(
            request,
            f"Welcome, {user.username}.",
        )

        ApplicationLogger.info(
            f"Template login completed: username={user.username}"
        )

        return redirect("accounts:dashboard")

    ApplicationLogger.warning("Template login validation failed.")

    return render(
        request,
        "accounts/login.html",
        {
            "errors": serializer.errors,
        },
        status=401,
    )


@login_required
@require_POST
def logout_view(request):
    username = request.user.username

    logout(request)

    messages.success(
        request,
        "You have been logged out.",
    )

    ApplicationLogger.info(
        f"Template logout completed: username={username}"
    )

    return redirect("accounts:login")


@login_required
def dashboard_view(request):
    ApplicationLogger.info(
        f"Dashboard requested: username={request.user.username}"
    )

    return render(
        request,
        "accounts/dashboard.html",
    )


@login_required
def profile_view(request):
    if request.method == "GET":
        ApplicationLogger.info(
            f"Profile page requested: username={request.user.username}"
        )

        return render(
            request,
            "accounts/profile.html",
        )

    serializer = UserSerializer(
        request.user,
        data=request.POST,
        partial=True,
    )

    if serializer.is_valid():
        user = serializer.save()

        messages.success(
            request,
            "Profile updated successfully.",
        )

        ApplicationLogger.info(
            f"Template profile updated: username={user.username}"
        )

        return redirect("accounts:profile")

    ApplicationLogger.warning(
        f"Template profile validation failed: username={request.user.username}"
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "errors": serializer.errors,
        },
        status=400,
    )


@login_required
def user_list_view(request):
    if request.user.role != User.Role.ADMIN:
        ApplicationLogger.warning(
            f"Unauthorized user management page access: "
            f"username={request.user.username}"
        )

        messages.error(
            request,
            "Only administrators can manage users.",
        )

        return redirect("accounts:dashboard")

    users = (
        User.objects
        .select_related("assigned_analyst")
        .all()
    )

    analysts = User.objects.filter(
        role=User.Role.ANALYST,
        is_active=True,
    )

    ApplicationLogger.info(
        f"Admin user list requested: username={request.user.username}"
    )

    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
            "analysts": analysts,
            "roles": User.Role.choices,
        },
    )


@login_required
@require_POST
def user_role_update_view(request, user_id):
    if request.user.role != User.Role.ADMIN:
        ApplicationLogger.warning(
            f"Unauthorized user role update attempt: "
            f"username={request.user.username}"
        )

        messages.error(
            request,
            "Only administrators can update users.",
        )

        return redirect("accounts:dashboard")

    user = get_object_or_404(User, id=user_id)

    if user.id == request.user.id:
        messages.error(
            request,
            "You cannot change your own role.",
        )

        ApplicationLogger.warning(
            f"Admin attempted to change own role: "
            f"username={request.user.username}"
        )

        return redirect("accounts:user-list")

    role = request.POST.get("role")
    assigned_analyst_id = request.POST.get("assigned_analyst")

    data = {
        "role": role,
        "assigned_analyst": assigned_analyst_id or None,
    }

    serializer = AdminUserUpdateSerializer(
        user,
        data=data,
        partial=True,
    )

    if serializer.is_valid():
        updated_user = serializer.save()

        messages.success(
            request,
            f"{updated_user.username} was updated successfully.",
        )

        ApplicationLogger.info(
            f"Template admin user update completed: "
            f"admin={request.user.username}, "
            f"user={updated_user.username}"
        )

        return redirect("accounts:user-list")

    ApplicationLogger.warning(
        f"Template admin user update validation failed: "
        f"admin={request.user.username}, "
        f"target={user.username}"
    )

    users = (
        User.objects
        .select_related("assigned_analyst")
        .all()
    )

    analysts = User.objects.filter(
        role=User.Role.ANALYST,
        is_active=True,
    )

    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
            "analysts": analysts,
            "roles": User.Role.choices,
            "errors": serializer.errors,
        },
        status=400,
    )