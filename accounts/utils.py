import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.core.cache import cache

from config.application_logger import ApplicationLogger
from .models import User


def get_token_auth_hash(user):
    return user.get_session_auth_hash()[:20]


def create_access_token(user):
    now = datetime.now(timezone.utc)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "auth_hash": get_token_auth_hash(user),
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
        "auth_hash": get_token_auth_hash(user),
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
    return cache.get(f"blacklisted_refresh:{jti}") is True                                      # blacklisted_refresh:abc123; The token would need to be the same to be detected as blacklisted


def blacklist_refresh_token(payload):
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not jti or not exp:
        return False

    remaining_seconds = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
    cache.set(f"blacklisted_refresh:{jti}", True, timeout=remaining_seconds)                    # blacklisted_refresh:abc123; The token would need to be the same to be detected as blacklisted
    ApplicationLogger.info(f"Refresh token blacklisted: jti={jti}")
    return True


def get_user_from_token_payload(payload):
    user = User.objects.filter(id=payload.get("user_id"), is_active=True).first()

    if user is None:
        ApplicationLogger.warning("Token contained an invalid or inactive user.")
        return None

    if payload.get("auth_hash") != get_token_auth_hash(user):
        ApplicationLogger.warning(f"Token issued before the last password change: username={user.username}")
        return None

    return user


def find_user_by_login(identifier):
    user = User.objects.filter(username=identifier).first()

    if user is None:
        user = User.objects.filter(email__iexact=identifier).first()

    return user