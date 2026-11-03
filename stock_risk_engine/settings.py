import os
from pathlib import Path
from celery.schedules import crontab

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
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

ROOT_URLCONF = 'stock_risk_engine.urls'
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

WSGI_APPLICATION = 'stock_risk_engine.wsgi.application'
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

MAILERS = {
    'default': { 'BACKEND': 'django.core.mail.backends.console.EmailBackend' },
}

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")

ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv("ACCESS_TOKEN_LIFETIME_MINUTES"))
REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS"))

REDIS_URL = os.getenv("REDIS_URL")
TOKEN_BLACKLIST_REDIS_URL = os.getenv("TOKEN_BLACKLIST_REDIS_URL")

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

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
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
    "retrain-models": {
        "task": "analytics.tasks.retrain_models",
        "schedule": crontab(hour=2, minute=0, day_of_week="sun"),
    },
}

# MARKET_SEED_TICKERS = [ticker.strip().upper() for ticker in os.getenv("MARKET_SEED_TICKERS", "").split(",") if ticker.strip()]
MARKET_SEED_TICKERS = []
for ticker in os.getenv("MARKET_SEED_TICKERS", "").split(","):
    if ticker.strip():
        MARKET_SEED_TICKERS.append(ticker.strip().upper())

ML_MODELS_DIR = BASE_DIR / "ml_models"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "config.exception_handler.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
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
# 192.168.0.105
# This change is to be made in flutter app's baseurl, django's settings.py


# redis-server
# celery -A stock_risk_engine worker -l info


# NOTES: https://docs.google.com/document/d/100nUGdp2ZRZcKDNrX7mGhSPQGnLvMLWaZF9840ImHCo/edit?tab=t.0#heading=h.tn77ef5fg1dv

# Dataset taken from:
# https://www.kaggle.com/datasets/innacampo/s-and-p-500-stocks-daily-historical-data-10-years

# source ../learning_django/env_machine_learning/bin/activate