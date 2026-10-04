import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directory for persistent storage (mapped volume in HA)
_default_data_dir = (
    Path("/data")
    if os.path.exists("/data") and os.access("/data", os.W_OK)
    else (BASE_DIR / "data")
)
DATA_DIR = Path(os.environ.get("DATA_DIR", _default_data_dir))

# SECURITY WARNING: keep the secret key secret in production
# In the HA app context, we use SUPERVISOR_TOKEN as the secret key
SECRET_KEY = os.environ.get("SUPERVISOR_TOKEN", "dev-insecure-key-change-me")

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "daphne",
    "django.contrib.staticfiles",
    "channels",
    "plans",
    "ha",
    "live",
]

MIDDLEWARE = [
    "securityhawk.middleware.IngressMiddleware",
    "kiosk.middleware.KioskTokenMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "securityhawk.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

ASGI_APPLICATION = "securityhawk.asgi.application"

# Channel layers — in-memory for single-process deployment
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# No database needed for plan data (JSON files), but Django needs one configured
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "collected_static"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "ha": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "live": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "plans": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# ---- Security Hawk Settings ----

# Plan storage paths
PLANS_DIR = DATA_DIR / "plans"
ASSETS_DIR = DATA_DIR / "assets"
VERSIONS_DIR = DATA_DIR / "versions"
MAX_VERSIONS = 20

# Max upload size for backgrounds (20MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

def _int_env(key: str, default: int) -> int:
    val = os.environ.get(key, "").strip()
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# Kiosk settings
KIOSK_ENABLED = os.environ.get("KIOSK_ENABLED", "false").lower() == "true"
KIOSK_PORT = _int_env("KIOSK_PORT", 8100)
KIOSK_TOKEN = os.environ.get("KIOSK_TOKEN", "")
QUIET_RETURN_SECONDS = _int_env("QUIET_RETURN", 120)
DEFAULT_VIEW = os.environ.get("DEFAULT_VIEW", "") or "overview"

# HA connection
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor"
HA_WS_URL = "ws://supervisor/core/websocket"
