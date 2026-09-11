from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from config.application_logger import ApplicationLogger
from .models import User


class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializer(serializers.ModelSerializer):
    assigned_analyst = MinimalUserSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "assigned_analyst", "date_joined"]
        read_only_fields = ["id", "role", "assigned_analyst", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        if password is None:
            raise serializers.ValidationError({"password": "Password is required."})

        user = User.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)         # Never save a new password as plain text.
        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.save()
        ApplicationLogger.info(f"Profile updated: username={instance.username}")
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirmation"]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirmation")
        user = User.objects.create_user(role=User.Role.INVESTOR, **validated_data)
        ApplicationLogger.info(f"Investor registration completed: username={user.username}")
        return user


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login_value = attrs["username_or_email"]
        password = attrs["password"]

        user = User.objects.filter(email__iexact=login_value).first()
        username = user.username if user else login_value
        authenticated_user = authenticate(username=username, password=password)

        if authenticated_user is None:
            ApplicationLogger.warning(f"Failed login attempt: identifier={login_value}")
            raise serializers.ValidationError("Invalid username/email or password.")

        if not authenticated_user.is_active:
            ApplicationLogger.warning(f"Inactive user attempted login: username={authenticated_user.username}")
            raise serializers.ValidationError("This account is inactive.")

        attrs["user"] = authenticated_user
        ApplicationLogger.info(f"Successful login: username={authenticated_user.username}")
        return attrs


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "assigned_analyst"]

    def validate(self, attrs):
        role = attrs.get("role", self.instance.role)
        analyst = attrs.get("assigned_analyst", self.instance.assigned_analyst)

        if role == User.Role.INVESTOR:
            if analyst and analyst.role != User.Role.ANALYST:
                raise serializers.ValidationError({"assigned_analyst": "Assigned user must be an analyst."})

        elif role == User.Role.ANALYST and analyst:
            raise serializers.ValidationError({"assigned_analyst": "Analysts cannot be assigned an analyst."})

        elif role == User.Role.ADMIN and analyst:
            raise serializers.ValidationError({"assigned_analyst": "Admins cannot have an assigned analyst."})
        return attrs

    def update(self, instance, validated_data):
        old_role = instance.role
        instance = super().update(instance, validated_data)
        ApplicationLogger.info(f"Admin updated user: username={instance.username}, role={old_role}->{instance.role}, assigned_analyst={instance.assigned_analyst_id}")
        return instance