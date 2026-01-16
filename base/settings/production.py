from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = [
    os.getenv("DOMAIN_NAME"),
    os.getenv("SERVER_IP"),
]

# ------------------
# Security (VERY IMPORTANT)
# ------------------

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ------------------
# Database (PostgreSQL)
# ------------------

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("POSTGRES_DB"),
    "USER": os.getenv("POSTGRES_USER"),
    "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
    "HOST": os.getenv("POSTGRES_HOST", "localhost"),
    "PORT": "5432",
}

# ------------------
# Static files
# ------------------

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# ------------------
# CORS
# ------------------



# ------------------
# Redis / Celery
# ------------------

CELERY_BROKER_URL = os.getenv("REDIS_URL")
CACHES["default"]["LOCATION"] = os.getenv("REDIS_URL")



LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/django_errors.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}



CSRF_TRUSTED_ORIGINS = [
    f"https://{os.getenv('DOMAIN_NAME')}",
]


CORS_ALLOWED_ORIGINS = [
    "https://tourtra.ma", 
    "http://localhost:3000", 
]