from django.contrib.auth.base_user import BaseUserManager
from config.application_logger import ApplicationLogger


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required.")

        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            raise ValueError("Password is required.")

        user.save(using=self._db)
        ApplicationLogger.info(f"User created: username={username}, role={user.role}")
        return user


    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("role", self.model.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("role") != self.model.Role.ADMIN:
            raise ValueError("Superuser must have admin role.")

        return self.create_user(username=username, email=email, password=password, **extra_fields)