import os
import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DEBUG=(bool, False),
)

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# -----------------------------------------------------------------------------
# Core security (see https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
# -----------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=env.bool("DEBUG", default=False))

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# HTTPS sites: list full origins, e.g. https://example.com
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Trust X-Forwarded-Proto only when behind nginx/Cloudflare/etc.
if env.bool("BEHIND_TLS_PROXY", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    SECURE_PROXY_SSL_HEADER = None

# Rate limiting & general abuse protection (django-ratelimit)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rental-finder-security-cache",
    }
}

# Limit oversized POST bodies / uploads (bytes)
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "DATA_UPLOAD_MAX_MEMORY_SIZE", default=6_291_456
)  # 6 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=6_291_456)

# Admin URL path - obscure default in production via ADMIN_URL_PATH in .env
ADMIN_URL_PATH = env("ADMIN_URL_PATH", default="admin/")
if ADMIN_URL_PATH and not ADMIN_URL_PATH.endswith("/"):
    ADMIN_URL_PATH = ADMIN_URL_PATH + "/"

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if not DEBUG:
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"


# Application definition

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "listings",
    "crispy_forms",
    "crispy_bootstrap5",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "listings.context_processors.reward_nav",
                "listings.context_processors.visitor_location",
                "listings.context_processors.assistant_limits",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# Use DATABASE_URL if set (e.g. on Render, Heroku). Format:
#   postgres://USER:PASSWORD@HOST:PORT/NAME   or   sqlite:////path/to/db.sqlite3
# Falls back to SQLite when DATABASE_URL is not provided.
_db_url = env("DATABASE_URL", default=None)
if _db_url:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / env("DB_NAME", default="db.sqlite3"),
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "listings.validators.UpperLowerSymbolPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "public"]

# WhiteNoise: serve collected static files directly from the app (no separate
# webserver needed). Compressed manifest for long cache expiry.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# AI Configuration
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
# AI assistant chat limits (session counter for guests; DB daily for users)
AI_ASSISTANT_GUEST_MESSAGE_CAP = 5
AI_ASSISTANT_USER_DAILY_CAP = 100

# -----------------------------------------------------------------------------
# Django admin UI (django-jazzmin): https://django-jazzmin.readthedocs.io/
# -----------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "HouseFinderBD - Control center",
    "site_header": "HouseFinderBD",
    "site_brand": "HouseFinderBD",
    "site_logo": "logo/favicon.jpeg",
    "site_icon": "logo/favicon.jpeg",
    "login_logo": "logo/logo.jpeg",
    "welcome_sign": "Operations console: analytics, moderation shortcuts, and full model access.",
    "copyright": "HouseFinderBD",
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": ["listings", "auth"],
    "related_modal_active": True,
    "custom_css": "admin/css/rental_admin.css",
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "show_theme_chooser": False,
    "default_theme_mode": "light",
    "custom_links": {
        "listings": [
            {
                "name": "Public homepage",
                "url": "/",
                "icon": "fas fa-globe",
                "new_window": True,
            },
            {
                "name": "Search listings",
                "url": "/search",
                "icon": "fas fa-search-location",
                "new_window": True,
            },
            {
                "name": "Landlord dashboard",
                "url": "/dashboard/",
                "icon": "fas fa-chart-line",
                "new_window": True,
            },
            {
                "name": "Rewards program",
                "url": "/rewards/",
                "icon": "fas fa-gift",
                "new_window": True,
            },
        ],
    },
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
        "listings": "fas fa-city",
        "listings.listing": "fas fa-home",
        "listings.listingimage": "fas fa-images",
        "listings.inquiry": "fas fa-envelope",
        "listings.favorite": "fas fa-heart",
        "listings.review": "fas fa-star",
        "listings.rewardwallet": "fas fa-wallet",
        "listings.pointsledger": "fas fa-list-alt",
        "listings.listingoffer": "fas fa-tags",
        "listings.aiassistantdailyusage": "fas fa-comments",
    },
    "default_icon_parents": "fas fa-folder-open",
    "default_icon_children": "fas fa-caret-right",
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
    },
    "search_model": ["auth.User", "listings.Listing", "listings.Inquiry"],
    "topmenu_links": [
        {"name": "Home", "url": "/", "new_window": True, "icon": "fas fa-home"},
        {
            "name": "Search",
            "url": "/search",
            "new_window": True,
            "icon": "fas fa-search",
        },
        {
            "name": "Landlord",
            "url": "/dashboard/",
            "new_window": True,
            "icon": "fas fa-tachometer-alt",
        },
        {
            "name": "Rewards",
            "url": "/rewards/",
            "new_window": True,
            "icon": "fas fa-award",
        },
    ],
    "usermenu_links": [
        {"name": "Public site", "url": "/", "new_window": True},
        {"name": "Landlord dashboard", "url": "/dashboard/", "new_window": True},
    ],
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "#06311f",
    "accent": "accent-success",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "button_classes": {
        "primary": "btn-success",
        "secondary": "btn-outline-secondary",
    },
}

# -----------------------------------------------------------------------------
# Logging (security-relevant events to console in production use file/syslog)
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
