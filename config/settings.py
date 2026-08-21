"""
Django settings for TradeFlow.

Development + production-ready configuration.

Django 6.1
TradeFlow
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

# Local development:
#
# tradeflow/
# └── .env
#
# Production hosting platforms such as Render provide
# environment variables directly.
#
# load_dotenv() does not override environment variables
# that are already supplied by the operating system.
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


# Production must provide DJANGO_SECRET_KEY through
# the hosting environment.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY"
)


if not SECRET_KEY:

    if DEBUG:

        # Development-only fallback.
        #
        # Never use this value as the production key.
        SECRET_KEY = (
            "tradeflow-development-only-"
            "replace-before-production"
        )

    else:

        raise RuntimeError(
            "DJANGO_SECRET_KEY must be set "
            "when DEBUG=False."
        )


# Local development defaults:
#
# http://127.0.0.1:8000
# http://localhost:8000
#
# Render production example:
#
# ALLOWED_HOSTS=tradeflow-04pz.onrender.com
ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
    ],
)


# Production example:
#
# CSRF_TRUSTED_ORIGINS=
# https://tradeflow-04pz.onrender.com
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


    # TradeFlow

    "core",

]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",


    # WhiteNoise serves the files created by collectstatic.
    #
    # It should remain directly after SecurityMiddleware.

    "whitenoise.middleware.WhiteNoiseMiddleware",


    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",


    # Attach a unique request ID to every incoming request.
    #
    # The middleware runs after authentication so later
    # error handlers can safely identify the signed-in user.

    "core.request_id.RequestIDMiddleware",


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


        # Also allow templates inside Django apps.

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

    # Production PostgreSQL.
    #
    # TradeFlow currently uses the Supabase
    # Session Pooler connection URL.

    DATABASES = {

        "default": dj_database_url.parse(

            DATABASE_URL,

            conn_max_age=600,

            conn_health_checks=True,

        )

    }

else:

    # Local SQLite fallback.
    #
    # This preserves the ability to run TradeFlow locally
    # without requiring PostgreSQL.

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


# Output directory created by:
#
# python manage.py collectstatic
STATIC_ROOT = (
    BASE_DIR
    / "staticfiles"
)


# Optional project-level source directory:
#
# tradeflow/
# └── static/
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
# PASSWORD RESET
# =========================================================

# Reset links remain valid for:
#
# 259200 seconds = 3 days.
PASSWORD_RESET_TIMEOUT = int(
    os.getenv(
        "PASSWORD_RESET_TIMEOUT",
        "259200",
    )
)


# =========================================================
# EMAIL / PASSWORD RESET DELIVERY
# =========================================================

# ---------------------------------------------------------
# LOCAL DEVELOPMENT
# ---------------------------------------------------------
#
# EMAIL_PROVIDER=console
#
# Password-reset messages are printed in the VS Code
# terminal. This keeps local development independent of
# external email services.
#
#
# ---------------------------------------------------------
# PRODUCTION / RENDER
# ---------------------------------------------------------
#
# EMAIL_PROVIDER=resend
#
# Production messages are sent through the Resend HTTPS
# API instead of SMTP.
#
# Render Free blocks outbound SMTP connections on the
# standard SMTP ports, so using Resend's HTTPS API avoids
# those restrictions completely.

EMAIL_PROVIDER = os.getenv(
    "EMAIL_PROVIDER",
    "console",
).strip().lower()


if EMAIL_PROVIDER == "resend":

    # Resend API secret.
    #
    # This value must be supplied by Render as:
    #
    # RESEND_API_KEY=re_...
    #
    # Never hard-code the actual API key here.

    RESEND_API_KEY = os.getenv(
        "RESEND_API_KEY",
        "",
    ).strip()


    # Production should never silently start with
    # the Resend provider selected but no API key.

    if not RESEND_API_KEY and not DEBUG:

        raise RuntimeError(
            "RESEND_API_KEY must be set "
            "when EMAIL_PROVIDER=resend "
            "in production."
        )


    # Django 6.1 mailer configuration.
    #
    # The custom backend translates Django email messages
    # into Resend HTTPS API requests.

    MAILERS = {

        "default": {

            "BACKEND": (
                "core.resend_backend."
                "ResendEmailBackend"
            ),

        },

    }


else:

    # Local development console mailer.
    #
    # This preserves the password-reset workflow already
    # tested successfully in VS Code.

    MAILERS = {

        "default": {

            "BACKEND": (
                "django.core.mail.backends.console."
                "EmailBackend"
            ),

        },

    }


# Sender displayed to users.
#
# During Resend testing:
#
# TradeFlow <onboarding@resend.dev>
#
# Once a TradeFlow domain is owned and verified,
# this can become something such as:
#
# TradeFlow <no-reply@tradeflow.co.za>

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "TradeFlow <onboarding@resend.dev>",
)


# Django uses SERVER_EMAIL for internal/system messages.
SERVER_EMAIL = os.getenv(
    "SERVER_EMAIL",
    DEFAULT_FROM_EMAIL,
)


# =========================================================
# OPENAI
# =========================================================

# views.py reads these environment variables directly.
#
# Never place the actual OpenAI API key in this file.
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

    # Force HTTP → HTTPS.

    SECURE_SSL_REDIRECT = True


    # Cookies may only travel over HTTPS.

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True


    # Prevent JavaScript access to the session cookie.

    SESSION_COOKIE_HTTPONLY = True


    # Sensible cross-site behavior.

    SESSION_COOKIE_SAMESITE = "Lax"

    CSRF_COOKIE_SAMESITE = "Lax"


    # HSTS.
    #
    # We deliberately start conservatively.
    #
    # Do not enable INCLUDE_SUBDOMAINS or PRELOAD while
    # TradeFlow is still using an onrender.com hostname.

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


    # Prevent TradeFlow pages from being embedded
    # in hostile frames.

    X_FRAME_OPTIONS = "DENY"


    # Render terminates HTTPS before forwarding traffic
    # to Gunicorn.
    #
    # This tells Django that X-Forwarded-Proto=https
    # represents a secure original request.

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


# =========================================================
# LOGGING / ERROR REPORTING
# =========================================================

# Render captures stdout/stderr automatically, so TradeFlow
# logs to the console rather than writing log files to disk.
#
# Production example:
#
# LOG_LEVEL=INFO
#
# For temporary deeper troubleshooting:
#
# LOG_LEVEL=DEBUG
#
# Avoid DEBUG logging permanently in production because it
# can create excessive output.

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).strip().upper()


LOGGING = {

    "version": 1,

    # Keep Django's existing built-in logging configuration
    # active alongside TradeFlow's handlers.
    "disable_existing_loggers": False,


    # -----------------------------------------------------
    # FORMATTERS
    # -----------------------------------------------------

    "formatters": {

        "verbose": {

            "format": (
                "{levelname} "
                "{asctime} "
                "{name} "
                "{message}"
            ),

            "style": "{",

        },


        "simple": {

            "format": (
                "{levelname}: "
                "{message}"
            ),

            "style": "{",

        },

    },


    # -----------------------------------------------------
    # HANDLERS
    # -----------------------------------------------------

    "handlers": {

        "console": {

            "class": (
                "logging.StreamHandler"
            ),

            "formatter": "verbose",

        },

    },


    # -----------------------------------------------------
    # ROOT LOGGER
    # -----------------------------------------------------

    "root": {

        "handlers": [
            "console",
        ],

        "level": LOG_LEVEL,

    },


    # -----------------------------------------------------
    # DJANGO + TRADEFLOW LOGGERS
    # -----------------------------------------------------

    "loggers": {

        # Real request failures such as HTTP 500 errors.
        "django.request": {

            "handlers": [
                "console",
            ],

            "level": "ERROR",

            "propagate": False,

        },


        # Database warnings/errors.
        "django.db.backends": {

            "handlers": [
                "console",
            ],

            "level": "WARNING",

            "propagate": False,

        },


        # Security events raised by Django.
        "django.security": {

            "handlers": [
                "console",
            ],

            "level": "WARNING",

            "propagate": False,

        },


        # TradeFlow application code.
        "core": {

            "handlers": [
                "console",
            ],

            "level": LOG_LEVEL,

            "propagate": False,

        },

    },

}


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)