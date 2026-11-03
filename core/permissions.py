from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User
from config.application_logger import ApplicationLogger


def get_owner(obj):
    if hasattr(obj, "user"):
        return obj.user

    if hasattr(obj, "portfolio"):
        return obj.portfolio.user

    return None


class IsAdminRole(BasePermission):
    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        allowed = request.user.is_authenticated and request.user.role == User.Role.ADMIN

        if not allowed:
            ApplicationLogger.warning(f"Admin permission denied: path={request.path}")

        return allowed


class IsAnalystOrAdminRole(BasePermission):
    message = "Only analysts and administrators can perform this action."

    def has_permission(self, request, view):
        allowed_roles = [User.Role.ANALYST, User.Role.ADMIN]
        allowed = request.user.is_authenticated and request.user.role in allowed_roles

        if not allowed:
            ApplicationLogger.warning(f"Analyst/Admin permission denied: path={request.path}")

        return allowed


class IsOwner(BasePermission):
    message = "You do not own this resource."

    def has_object_permission(self, request, view, obj):
        owner = get_owner(obj)
        return owner is not None and owner.id == request.user.id


class IsAssignedAnalyst(BasePermission):
    message = "You are not the analyst assigned to this investor."

    def has_object_permission(self, request, view, obj):
        owner = get_owner(obj)

        if owner is None:
            return False

        if request.user.role != User.Role.ANALYST:
            return False

        if request.method not in SAFE_METHODS:
            return False

        return owner.assigned_analyst_id == request.user.id


class IsOwnerOrAssignedAnalystOrAdmin(BasePermission):
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True

        if IsOwner().has_object_permission(request, view, obj):
            return True

        if IsAssignedAnalyst().has_object_permission(request, view, obj):
            return True

        ApplicationLogger.warning(f"Object permission denied: user={request.user.username}, path={request.path}")
        return False
