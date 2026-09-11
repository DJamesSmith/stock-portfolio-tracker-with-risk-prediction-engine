from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from config.application_logger import ApplicationLogger
from .models import User
from .permissions import IsAdmin
from .serializers import AdminUserUpdateSerializer, LoginSerializer, RegisterSerializer, UserSerializer
from .utils import blacklist_refresh_token, create_token_pair, decode_refresh_token, get_user_from_token_payload, is_refresh_token_blacklisted, create_access_token


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            ApplicationLogger.warning("Registration validation failed.")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        ApplicationLogger.info(f"Registration API completed: username={user.username}")

        return Response({
                "message": "Investor account created successfully.",
                "user": UserSerializer(user).data,
            }, status=status.HTTP_201_CREATED,)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data["user"]
        tokens = create_token_pair(user)

        return Response({
                "message": "Login successful.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        payload = decode_refresh_token(refresh_token)

        if payload is None:
            return Response({ "detail": "Invalid or expired refresh token." }, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("token_type") != "refresh":
            return Response({ "detail": "Refresh token required." }, status=status.HTTP_401_UNAUTHORIZED)

        if is_refresh_token_blacklisted(payload.get("jti")):
            return Response({ "detail": "Refresh token has been invalidated." }, status=status.HTTP_401_UNAUTHORIZED)

        user = get_user_from_token_payload(payload)

        if user is None:
            return Response({ "detail": "User no longer exists." }, status=status.HTTP_401_UNAUTHORIZED)

        access_token = create_access_token(user)["access"]
        ApplicationLogger.info(f"Access token refreshed: username={user.username}")

        return Response({ "access": access_token }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({ "detail": "Refresh token is required." }, status=status.HTTP_400_BAD_REQUEST)

        payload = decode_refresh_token(refresh_token)

        if payload is None:
            return Response({ "detail": "Invalid or expired refresh token." }, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("token_type") != "refresh":
            return Response({ "detail": "Refresh token required." }, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("user_id") != request.user.id:
            return Response({ "detail": "Refresh token does not belong to this user." }, status=status.HTTP_403_FORBIDDEN)

        blacklist_refresh_token(payload)

        ApplicationLogger.info(f"Logout completed: username={request.user.username}")

        return Response({ "message": "Logout successful." }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ApplicationLogger.info(f"Profile requested: username={request.user.username}")
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        ApplicationLogger.info(f"Profile updated: username={user.username}")
        return Response(UserSerializer(user).data)


class UserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.select_related("assigned_analyst").all()
        data = [UserSerializer(user).data for user in users]
        ApplicationLogger.info(f"Admin listed users: count={len(data)}")
        return Response(data)


class UserRoleUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            ApplicationLogger.warning(f"Admin attempted to update missing user: id={user_id}")
            return Response({ "detail": "User not found." }, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_user = serializer.save()
        return Response(UserSerializer(updated_user).data)