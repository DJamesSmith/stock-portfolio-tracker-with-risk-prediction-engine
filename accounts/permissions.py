from rest_framework.permissions import BasePermission
from core.application_logger import ApplicationLogger
from .models import User


class IsAdmin(BasePermission):
    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        allowed = bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN)

        if not allowed:
            ApplicationLogger.warning(f"Admin permission denied: user={getattr(request.user, 'username', None)}")
        return allowed


class IsInvestor(BasePermission):
    message = "Only investors can perform this action."

    def has_permission(self, request, view):
        allowed = bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.INVESTOR)

        if not allowed:
            ApplicationLogger.warning(f"Investor permission denied: user={getattr(request.user, 'username', None)}")

        return allowed


class IsAnalyst(BasePermission):
    message = "Only analysts can perform this action."

    def has_permission(self, request, view):
        allowed = bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ANALYST)

        if not allowed:
            ApplicationLogger.warning(f"Analyst permission denied: user={getattr(request.user, 'username', None)}")

        return allowed


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        allowed = (
            request.user.role == User.Role.ADMIN
            or obj.id == request.user.id)

        if not allowed:
            ApplicationLogger.warning(f"Object permission denied: requester={request.user.username}, target={obj.username}")

        return allowed