from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        INVESTOR = "investor", "Investor"
        ANALYST = "analyst", "Analyst"
        ADMIN = "admin", "Admin"

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.INVESTOR)

    assigned_analyst = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_investors",
        limit_choices_to={"role": Role.ANALYST})

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        ordering = ["id"]

    def __str__(self):
        return f"{self.username} ({self.role})"

    def save(self, *args, **kwargs):
        if self.role != self.Role.INVESTOR:
            self.assigned_analyst = None

        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)


# Django created "users" for your actual User model.
    
# The other two:
# users_groups
# users_user_permissions

# come from:
# PermissionsMixin

# because your custom user inherits:
# AbstractBaseUser, PermissionsMixin

# PermissionsMixin gives the user model Django's permission/group relationships.

# ----------------------------------------------------------------------------------------------------