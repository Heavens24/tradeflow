"""
Django settings for TradeFlow.

Development + production-ready configuration.

Django 6.1
TradeFlow MVP
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

# Load variables from:
#
# tradeflow/.env
#
# This is mainly useful during local development.
#
# Production hosting platforms normally provide
# environment variables directly.
load_dotenv(
    BASE_DIR / ".env"
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def env_bool(name, default=False):
    """
    Read a True/False environment variable safely.
    """

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name, default=None):
    """
    Read comma-separated environment variables.

    Example:
    ALLOWED_HOSTS=tradeflow.example.com,www.example.com
    """

    if default is None:
        default = []

    value = os.getenv(
        name,
        "",
    ).strip()

    if not value:
        return default

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# =========================================================
# SECURITY
# =========================================================

DEBUG = env_bool(
    "DEBUG",
    default=True,
)


# Development fallback only.
#
# Production MUST provide DJANGO_SECRET_KEY
# through the hosting environment.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY"
)


if not SECRET_KEY:

    if DEBUG:

        # Safe only for local development.
        #
        # Do NOT use this production fallback
        # as a deployed secret.
        SECRET_KEY = (
            "tradeflow-development-only-"
            "replace-before-production"
        )

    else:

        raise RuntimeError(
            "DJANGO_SECRET_KEY must be set "
            "when DEBUG=False."
        )


# Local development hosts are included automatically.
#
# Production hosts are provided through:
#
# ALLOWED_HOSTS=example.com,www.example.com

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
    ],
)


# Required for HTTPS POST requests from the
# deployed application's domain.
#
# Example:
#
# CSRF_TRUSTED_ORIGINS=https://tradeflow.example.com

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=[],
)


# =========================================================
# INSTALLED APPLICATIONS
# =========================================================

INSTALLED_APPS = [

    # Django built-in applications

    "django.contrib.admin",

    "django.contrib.auth",

    "django.contrib.contenttypes",

    "django.contrib.sessions",

    "django.contrib.messages",

    "django.contrib.staticfiles",


    # TradeFlow applications

    "core",

]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",


    # WhiteNoise serves collected static files
    # when TradeFlow is deployed.

    "whitenoise.middleware.WhiteNoiseMiddleware",


    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",

]


# =========================================================
# URL CONFIGURATION
# =========================================================

ROOT_URLCONF = "config.urls"


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [

    {

        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),


        # Project-level templates:
        #
        # tradeflow/
        # └── templates/
        #     └── core/

        "DIRS": [
            BASE_DIR / "templates",
        ],


        # Also allows templates located inside
        # individual Django applications.

        "APP_DIRS": True,


        "OPTIONS": {

            "context_processors": [

                (
                    "django.template.context_processors."
                    "request"
                ),

                (
                    "django.contrib.auth."
                    "context_processors.auth"
                ),

                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),

            ],

        },

    },

]


# =========================================================
# WSGI
# =========================================================

WSGI_APPLICATION = "config.wsgi.application"


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "",
).strip()


if DATABASE_URL:

    # Production PostgreSQL database.
    #
    # Deployment platforms commonly provide
    # DATABASE_URL automatically.

    DATABASES = {

        "default": dj_database_url.parse(

            DATABASE_URL,

            conn_max_age=600,

            conn_health_checks=True,

        )

    }

else:

    # Local development database.
    #
    # Existing SQLite development data remains
    # available exactly as before.

    DATABASES = {

        "default": {

            "ENGINE": (
                "django.db.backends.sqlite3"
            ),

            "NAME": (
                BASE_DIR
                / "db.sqlite3"
            ),

        }

    }


# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [

    {

        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "UserAttributeSimilarityValidator"
        ),

    },

    {

        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "MinimumLengthValidator"
        ),

    },

    {

        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "CommonPasswordValidator"
        ),

    },

    {

        "NAME": (
            "django.contrib.auth."
            "password_validation."
            "NumericPasswordValidator"
        ),

    },

]


# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = "en-za"

TIME_ZONE = "Africa/Johannesburg"

USE_I18N = True

USE_TZ = True


# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "/static/"


# Files generated by:
#
# python manage.py collectstatic

STATIC_ROOT = (
    BASE_DIR
    / "staticfiles"
)


# Source static directory.
#
# Only enable it if the folder exists so local
# development is not broken.

STATIC_SOURCE_DIR = (
    BASE_DIR
    / "static"
)


if STATIC_SOURCE_DIR.exists():

    STATICFILES_DIRS = [
        STATIC_SOURCE_DIR,
    ]


# Django 6.x storage configuration.

STORAGES = {

    "default": {

        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),

    },


    "staticfiles": {

        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),

    },

}


# =========================================================
# AUTHENTICATION
# =========================================================

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = "/dashboard/"

LOGOUT_REDIRECT_URL = "/login/"


# =========================================================
# EMAIL
# =========================================================

# Development:
# emails are shown in the terminal.
#
# Production email provider can be configured later.

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    (
        "django.core.mail.backends."
        "console.EmailBackend"
    ),
)


# =========================================================
# OPENAI
# =========================================================

# views.py reads these environment variables directly.
#
# NEVER place the real OpenAI key here.

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5-mini",
)


# =========================================================
# PRODUCTION SECURITY
# =========================================================

if not DEBUG:

    # Require HTTPS.

    SECURE_SSL_REDIRECT = True


    # Cookies must only travel over HTTPS.

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True


    # Session cookie cannot be read by JavaScript.

    SESSION_COOKIE_HTTPONLY = True


    # Sensible cross-site protection.

    SESSION_COOKIE_SAMESITE = "Lax"

    CSRF_COOKIE_SAMESITE = "Lax"


    # Browser HTTPS memory.
    #
    # We start conservatively.
    # Increase after the deployed HTTPS site
    # has been thoroughly tested.

    SECURE_HSTS_SECONDS = int(
        os.getenv(
            "SECURE_HSTS_SECONDS",
            "3600",
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        default=False,
    )

    SECURE_HSTS_PRELOAD = env_bool(
        "SECURE_HSTS_PRELOAD",
        default=False,
    )


    # Prevent MIME-type sniffing.

    SECURE_CONTENT_TYPE_NOSNIFF = True


    # Keep TradeFlow pages from being framed.

    X_FRAME_OPTIONS = "DENY"


    # Most production hosting services terminate
    # HTTPS at a reverse proxy/load balancer.
    #
    # X-Forwarded-Proto tells Django whether the
    # original connection used HTTPS.

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)