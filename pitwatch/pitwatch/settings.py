import os
import ssl
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary",
    "cloudinary_storage",
    "corsheaders",
    "rest_framework",
    "accounts",
    "dashboard",
    "ml",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = "pitwatch.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pitwatch.wsgi.application"
AUTH_USER_MODEL = "accounts.User"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "pitwatch"),
        "USER": os.getenv("DB_USER", "pitwatch_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "pitwatch_pass"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {"sslmode": os.getenv("DB_SSLMODE", "require")},
        "CONN_MAX_AGE": 60,
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY", ""),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET", ""),
}

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=3000),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", str(not DEBUG)).lower() == "true"
JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "None")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("CACHE_URL", "redis://localhost:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 300,
    }
}

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_IGNORE_RESULT = False
CELERY_RESULT_EXPIRES = 3600

if CELERY_BROKER_URL.startswith("rediss://"):
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

if CELERY_RESULT_BACKEND.startswith("rediss://"):
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False").lower() == "true"
CORS_ALLOW_CREDENTIALS = True


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"

# Email (Brevo API)
BREVO_API_URL = os.getenv("BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "PitWatch")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", BREVO_SENDER_EMAIL or "no-reply@pitwatch.local")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)