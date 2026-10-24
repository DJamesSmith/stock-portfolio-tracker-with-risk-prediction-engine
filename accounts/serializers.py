from rest_framework import serializers
from .models import User


class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializer(serializers.ModelSerializer):
    assigned_analyst = MinimalUserSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "assigned_analyst", "is_active", "date_joined", "updated_at"]
        read_only_fields = fields