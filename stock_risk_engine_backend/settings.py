import os
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def env_required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set in the .env file.")
    return value

SECRET_KEY = env_required("SECRET_KEY")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "10.0.2.2", "192.168.0.105"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',                       # added library to env to handle asynchronous protocols like WebSockets, HTTP/2, and long-polling in Django applications
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',

    # Local apps
    'accounts',
    'core',
    'market_data',
    'portfolios',
    'analytics',
    'dashboards',
    'ml_training',
    'monitoring',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "corsheaders.middleware.CorsMiddleware",                            # added
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'stock_risk_engine_backend.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'stock_risk_engine_backend.wsgi.application'
ASGI_APPLICATION = 'stock_risk_engine_backend.asgi.application'
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     os.getenv("DB_NAME"),
        "USER":     os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST":     os.getenv("DB_HOST"),
        "PORT":     os.getenv("DB_PORT"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator' },
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [ BASE_DIR / "script" ]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

JWT_SECRET_KEY = env_required("JWT_SECRET_KEY")
JWT_REFRESH_SECRET_KEY = env_required("JWT_REFRESH_SECRET_KEY")

ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv("ACCESS_TOKEN_LIFETIME_MINUTES"))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS"))

REDIS_URL = env_required("REDIS_URL")
TOKEN_BLACKLIST_REDIS_URL = env_required("TOKEN_BLACKLIST_REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
    "token_blacklist": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": TOKEN_BLACKLIST_REDIS_URL,
    },
}

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS"))

CELERY_BROKER_URL = env_required("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env_required("CELERY_RESULT_BACKEND")
CHANNEL_LAYER_REDIS_URL = env_required("CHANNEL_LAYER_REDIS_URL")

if len({CELERY_BROKER_URL, CELERY_RESULT_BACKEND, REDIS_URL, TOKEN_BLACKLIST_REDIS_URL, CHANNEL_LAYER_REDIS_URL}) != 5:
    raise ImproperlyConfigured("CELERY_BROKER_URL, CELERY_RESULT_BACKEND, REDIS_URL, TOKEN_BLACKLIST_REDIS_URL and CHANNEL_LAYER_REDIS_URL must each use a different Redis database.")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [{"address": CHANNEL_LAYER_REDIS_URL, "socket_timeout": 10}]},
    },
}

CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True

CELERY_BEAT_SCHEDULE = {
    "ping-every-15-minutes": {
        "task": "core.tasks.ping",
        "schedule": 15 * 60,
    },
    "fetch-daily-prices": {
        "task": "market_data.tasks.fetch_daily_prices",
        "schedule": crontab(hour=22, minute=0, day_of_week="mon-fri"),
    },
    "recompute-holding-risk": {
        "task": "analytics.tasks.recompute_holding_risk",
        "schedule": crontab(hour=23, minute=0, day_of_week="mon-fri"),
    },
    "recompute-holding-forecast": {
        "task": "analytics.tasks.recompute_holding_forecast",
        "schedule": crontab(hour=23, minute=15, day_of_week="mon-fri"),
    },
    "poll-live-prices": {
        "task": "monitoring.tasks.poll_live_prices",
        "schedule": crontab(minute="*/2", hour="13-21", day_of_week="mon-fri"),
    },
    "retrain-models": {
        "task": "ml_training.tasks.retrain_models",
        "schedule": crontab(hour=2, minute=0, day_of_week="sun"),
    },
}

# MARKET_SEED_TICKERS = [ticker.strip().upper() for ticker in os.getenv("MARKET_SEED_TICKERS", "").split(",") if ticker.strip()]
MARKET_SEED_TICKERS = []
for ticker in os.getenv("MARKET_SEED_TICKERS", "").split(","):
    if ticker.strip():
        MARKET_SEED_TICKERS.append(ticker.strip().upper())

ML_MODELS_DIR = BASE_DIR / "ml_models"

MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_NUMBER_FILES = 1000

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "NUM_PROXIES": 0,
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("LOGIN_THROTTLE_RATE", "5/minute"),
        "register": os.getenv("REGISTER_THROTTLE_RATE", "10/hour"),
        "market_refresh": os.getenv("MARKET_REFRESH_THROTTLE_RATE", "10/hour"),
    },
}

CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']

# psql -U django_user -d stock_risk_prediction_db
# CREATE DATABASE stock_risk_prediction_db OWNER django_user;


# how to find my Mac's IP ?
# ipconfig getifaddr en0
# 192.168.0.103
# This change is to be made in flutter app's baseurl, django's settings.py
# python manage.py runserver 0.0.0.0:8000

# redis-server
# celery -A stock_risk_engine_backend worker -l info --pool=solo


# NOTES: https://docs.google.com/document/d/100nUGdp2ZRZcKDNrX7mGhSPQGnLvMLWaZF9840ImHCo/edit?tab=t.0#heading=h.tn77ef5fg1dv

# Dataset taken from:
# https://www.kaggle.com/datasets/innacampo/s-and-p-500-stocks-daily-historical-data-10-years

# source ../learning_django/env_machine_learning/bin/activate