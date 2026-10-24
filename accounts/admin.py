from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User

    list_display = ("id", "username", "email", "role", "assigned_analyst", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    readonly_fields = ("is_staff", "is_superuser", "last_login", "date_joined", "updated_at")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal information", {"fields": ("email",)}),
        ("Role and assignment", {"fields": ("role", "assigned_analyst")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "role", "is_active"),
            },
        ),
    )

    search_fields = ("username", "email")
    ordering = ("id",)