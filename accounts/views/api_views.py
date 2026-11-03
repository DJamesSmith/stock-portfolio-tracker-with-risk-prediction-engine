from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from config.application_logger import ApplicationLogger
from config.responses import api_response, get_form_errors
from core.cache import invalidate_admin_dashboard, invalidate_user_dashboards
from core.pagination import StandardPagination
from core.throttles import LoginRateThrottle, RegisterRateThrottle
from ..forms import (
    AdminUserUpdateForm,
    ChangePasswordForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    build_admin_update_data,
    build_profile_data,
)
from ..models import User
from ..permissions import IsAdmin
from ..serializers import UserSerializer
from ..utils import (
    blacklist_refresh_token,
    create_access_token,
    create_token_pair,
    decode_refresh_token,
    find_user_by_login,
    get_user_from_token_payload,
    is_refresh_token_blacklisted,
)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def register_api(request):
    form = RegisterForm(request.data)

    if not form.is_valid():
        ApplicationLogger.warning("Registration validation failed.")
        return api_response(
            "Registration failed.",
            errors=get_form_errors(form),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = form.save()
    invalidate_admin_dashboard()
    return api_response(
        "Investor account created successfully.",
        data=UserSerializer(user).data,
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_api(request):
    form = LoginForm(request.data)

    if not form.is_valid():
        return api_response(
            "Username or email and password are required.",
            errors=get_form_errors(form),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    identifier = form.cleaned_data["username_or_email"]
    password = form.cleaned_data["password"]
    user = find_user_by_login(identifier)

    if user is None or not user.check_password(password):
        ApplicationLogger.warning(f"Failed login attempt: identifier={identifier}")
        return api_response("Invalid username/email or password.", status_code=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        ApplicationLogger.warning(f"Inactive user attempted login: username={user.username}")
        return api_response("This account is inactive.", status_code=status.HTTP_403_FORBIDDEN)

    ApplicationLogger.info(f"Successful API login: username={user.username}")
    data = {
        "user": UserSerializer(user).data,
        "tokens": create_token_pair(user),
    }
    return api_response("Login successful.", data=data)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token_api(request):
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return api_response(
            "Refresh token is required.",
            errors={"refresh": ["This field is required."]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    payload = decode_refresh_token(refresh_token)

    if payload is None:
        return api_response("Invalid or expired refresh token.", status_code=status.HTTP_401_UNAUTHORIZED)

    if payload.get("token_type") != "refresh":
        return api_response("Refresh token required.", status_code=status.HTTP_401_UNAUTHORIZED)

    if is_refresh_token_blacklisted(payload.get("jti")):
        return api_response("Refresh token has been invalidated.", status_code=status.HTTP_401_UNAUTHORIZED)

    user = get_user_from_token_payload(payload)

    if user is None:
        return api_response("Refresh token is no longer valid. Please log in again.", status_code=status.HTTP_401_UNAUTHORIZED)

    access_token = create_access_token(user)
    ApplicationLogger.info(f"Access token refreshed: username={user.username}")
    return api_response("Access token refreshed.", data={"access": access_token})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_api(request):
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return api_response(
            "Refresh token is required.",
            errors={"refresh": ["This field is required."]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    payload = decode_refresh_token(refresh_token)

    if payload is None:
        return api_response("Invalid or expired refresh token.", status_code=status.HTTP_401_UNAUTHORIZED)

    if payload.get("token_type") != "refresh":
        return api_response("Refresh token required.", status_code=status.HTTP_401_UNAUTHORIZED)

    if payload.get("user_id") != request.user.id:
        return api_response("Refresh token does not belong to this user.", status_code=status.HTTP_403_FORBIDDEN)

    blacklist_refresh_token(payload)
    ApplicationLogger.info(f"API logout completed: username={request.user.username}")
    return api_response("Logout successful.")


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_api(request):
    if request.method == "GET":
        ApplicationLogger.info(f"Profile requested: username={request.user.username}")
        return api_response("Profile retrieved.", data=UserSerializer(request.user).data)

    if "password" in request.data:
        return api_response(
            "Profile update failed.",
            errors={"password": ["Use /api/accounts/change-password/ to change your password."]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    form = ProfileForm(build_profile_data(request.user, request.data), instance=request.user)

    if not form.is_valid():
        return api_response(
            "Profile update failed.",
            errors=get_form_errors(form),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = form.save()
    ApplicationLogger.info(f"Profile updated: username={user.username}")
    return api_response("Profile updated successfully.", data=UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    form = ChangePasswordForm(request.user, request.data)

    if not form.is_valid():
        return api_response(
            "Password change failed.",
            errors=get_form_errors(form),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = form.save()
    data = {"tokens": create_token_pair(user)}
    return api_response("Password changed successfully. Older tokens no longer work.", data=data)


@api_view(["GET"])
@permission_classes([IsAdmin])
def user_list_api(request):
    users = User.objects.select_related("assigned_analyst").order_by("id")

    paginator = StandardPagination()
    page = paginator.paginate_queryset(users, request)

    data = {
        "count": paginator.page.paginator.count,
        "next": paginator.get_next_link(),
        "previous": paginator.get_previous_link(),
        "results": UserSerializer(page, many=True).data,
    }

    ApplicationLogger.info(f"Admin listed users: admin={request.user.username}, count={data['count']}")
    return api_response("Users retrieved.", data=data)


@api_view(["PATCH"])
@permission_classes([IsAdmin])
def user_update_api(request, user_id):
    user = User.objects.filter(id=user_id).first()

    if user is None:
        ApplicationLogger.warning(f"Admin attempted to update missing user: id={user_id}")
        return api_response("User not found.", status_code=status.HTTP_404_NOT_FOUND)

    if user.id == request.user.id:
        ApplicationLogger.warning(f"Admin attempted to change own role: username={request.user.username}")
        return api_response("You cannot change your own role.", status_code=status.HTTP_403_FORBIDDEN)

    old_analyst_id = user.assigned_analyst_id
    form = AdminUserUpdateForm(build_admin_update_data(user, request.data), instance=user)

    if not form.is_valid():
        return api_response(
            "User update failed.",
            errors=get_form_errors(form),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    updated_user = form.save()
    invalidate_user_dashboards([updated_user.id, old_analyst_id, updated_user.assigned_analyst_id])
    return api_response("User updated successfully.", data=UserSerializer(updated_user).data)