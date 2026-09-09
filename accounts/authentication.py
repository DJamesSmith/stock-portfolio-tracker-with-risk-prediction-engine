from rest_framework import authentication, exceptions
from config.application_logger import ApplicationLogger
from .utils import decode_access_token, get_user_from_token_payload


# Authorization: Bearer <access-token>
class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        parts = authorization.split()

        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("Authorization header must use: Bearer <token>.")

        token = parts[1]
        payload = decode_access_token(token)

        if payload is None:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        if payload.get("token_type") != "access":
            raise exceptions.AuthenticationFailed("Access token required.")

        user = get_user_from_token_payload(payload)

        if user is None:
            raise exceptions.AuthenticationFailed("User no longer exists.")

        ApplicationLogger.info(f"Authenticated API request: username={user.username}, path={request.path}")
        return user, token