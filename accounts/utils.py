from datetime import datetime, timedelta, timezone
import uuid
import jwt
from django.conf import settings
from django.core.cache import cache
from config.application_logger import ApplicationLogger
from .models import User


def create_access_token(user):
    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "token_type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES),
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    ApplicationLogger.info(f"Access token created: username={user.username}")
    return token


def create_refresh_token(user):
    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user.id,
        "token_type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_LIFETIME_DAYS),
    }

    token = jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm="HS256")
    ApplicationLogger.info(f"Refresh token created: username={user.username}, jti={payload['jti']}")
    return token


def create_token_pair(user):
    return {
        "access": create_access_token(user),
        "refresh": create_refresh_token(user),
    }


def decode_access_token(token):
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        ApplicationLogger.warning(f"Access token validation failed: {exc}")
        return None


def decode_refresh_token(token):
    try:
        return jwt.decode(token, settings.JWT_REFRESH_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        ApplicationLogger.warning(f"Refresh token validation failed: {exc}")
        return None


def is_refresh_token_blacklisted(jti):
    return cache.get(f"blacklisted_refresh:{jti}") is True


def blacklist_refresh_token(payload):
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not jti or not exp:
        return False

    remaining_seconds = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
    cache.set(f"blacklisted_refresh: {jti}", True, timeout=remaining_seconds)
    ApplicationLogger.info(f"Refresh token blacklisted: jti={jti}")
    return True


def get_user_from_token_payload(payload):
    try:
        return User.objects.get(id=payload["user_id"], is_active=True)
    except (User.DoesNotExist, KeyError):
        ApplicationLogger.warning("Token contained an invalid or inactive user.")
        return None