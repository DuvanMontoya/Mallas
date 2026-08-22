from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


_load_env_file(PROJECT_ROOT / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=false.")
    SECRET_KEY = "insecure-development-key-only-never-use-in-production"
if not DEBUG and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must contain at least 50 characters when DJANGO_DEBUG=false."
    )
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
DEVELOPMENT_WEB_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3100",
    "http://127.0.0.1:3100",
)


def _default_web_origins(*, debug: bool) -> str:
    """Keep loopback browser origins available only in local development."""

    return ",".join(DEVELOPMENT_WEB_ORIGINS) if debug else ""


DEFAULT_WEB_ORIGINS = _default_web_origins(debug=DEBUG)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", DEFAULT_WEB_ORIGINS).split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", DEFAULT_WEB_ORIGINS).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "modules.common",
    "modules.identity",
    "modules.institutions",
    "modules.curriculum",
    "modules.rules",
    "modules.audit",
    "modules.student_records",
    "modules.offerings",
    "modules.planning",
    "modules.optimization",
    "modules.governance",
    "modules.imports",
    "modules.notifications",
    "modules.analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "modules.identity.middleware.OriginAndSecurityMiddleware",
    "modules.observability.middleware.ObservabilityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "modules.identity.middleware.PrivilegedMfaSessionMiddleware",
    "modules.identity.middleware.PasswordChangeSessionMiddleware",
    "modules.identity.middleware.InitialPasswordChangeRequiredMiddleware",
    "modules.identity.middleware.MutationRateLimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
CSRF_FAILURE_VIEW = "modules.common.api.csrf_failure"

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def database_from_environment() -> dict[str, object]:
    url = os.environ.get("DATABASE_URL")
    if not url or url.startswith("sqlite"):
        name = url.removeprefix("sqlite:///") if url else str(PROJECT_ROOT / "local.sqlite3")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name}
    parsed = urlparse(url)
    engine = (
        "django.db.backends.postgresql"
        if parsed.scheme in {"postgres", "postgresql"}
        else "django.db.backends.sqlite3"
    )
    if engine.endswith("sqlite3"):
        return {"ENGINE": engine, "NAME": str(PROJECT_ROOT / "local.sqlite3")}
    return {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
    }


DATABASES = {"default": database_from_environment()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = os.environ.get("APP_TIME_ZONE", "America/Bogota")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "identity.User"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "curriculum_session"
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", str(60 * 60 * 8)))
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "false").lower() == "true"
SECURE_SSL_REDIRECT = (
    os.environ.get("SECURE_SSL_REDIRECT", "false" if DEBUG else "true").lower() == "true"
)
if os.environ.get("SECURE_PROXY_SSL_HEADER", "").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "false").lower() in {
    "1",
    "true",
    "yes",
}

CONTENT_SECURITY_POLICY = os.environ.get(
    "CONTENT_SECURITY_POLICY",
    "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'",
)
PUBLIC_APP_URL = os.environ.get(
    "PUBLIC_APP_URL", os.environ.get("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@curriculum.local")
PASSWORD_RESET_EMAIL_ENABLED = os.environ.get("PASSWORD_RESET_EMAIL_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
}
NOTIFICATIONS_EMAIL_ENABLED = os.environ.get("NOTIFICATIONS_EMAIL_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
}
ANALYTICS_MIN_CELL_SIZE = int(os.environ.get("ANALYTICS_MIN_CELL_SIZE", "5"))
ANALYTICS_PSEUDONYMIZATION_KEY = os.environ.get("ANALYTICS_PSEUDONYMIZATION_KEY", SECRET_KEY)
PRIVATE_IMPORT_STORAGE_ROOT = os.environ.get(
    "PRIVATE_IMPORT_STORAGE_ROOT", str(PROJECT_ROOT / "var" / "private-imports")
)
HISTORY_PDF_PARSE_TIMEOUT_SECONDS = float(os.environ.get("HISTORY_PDF_PARSE_TIMEOUT_SECONDS", "15"))
HISTORY_PDF_PARSE_MEMORY_MIB = int(os.environ.get("HISTORY_PDF_PARSE_MEMORY_MIB", "384"))
HISTORY_RAW_PAYLOAD_RETENTION_DAYS = int(os.environ.get("HISTORY_RAW_PAYLOAD_RETENTION_DAYS", "30"))
if HISTORY_PDF_PARSE_TIMEOUT_SECONDS <= 0 or HISTORY_PDF_PARSE_MEMORY_MIB <= 0:
    raise ImproperlyConfigured("PDF parser timeout and memory settings must be positive")
EMAIL_VERIFICATION_REQUIRED = os.environ.get(
    "AUTH_EMAIL_VERIFICATION_REQUIRED", "false" if DEBUG else "true"
).lower() in {"1", "true", "yes"}
AUTH_RATE_LIMIT_PER_MINUTE = int(os.environ.get("AUTH_RATE_LIMIT_PER_MINUTE", "5"))
AUTH_RATE_LIMIT_IP_PER_MINUTE = int(os.environ.get("AUTH_RATE_LIMIT_IP_PER_MINUTE", "30"))
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", str(60 * 60)))
API_MUTATION_RATE_LIMIT_PER_MINUTE = int(
    os.environ.get("API_MUTATION_RATE_LIMIT_PER_MINUTE", "120")
)
API_UPLOAD_RATE_LIMIT_PER_MINUTE = int(os.environ.get("API_UPLOAD_RATE_LIMIT_PER_MINUTE", "10"))
API_GOVERNANCE_RATE_LIMIT_PER_MINUTE = int(
    os.environ.get("API_GOVERNANCE_RATE_LIMIT_PER_MINUTE", "60")
)
PRIVILEGED_MFA_REQUIRED = os.environ.get(
    "PRIVILEGED_MFA_REQUIRED", "false" if DEBUG else "true"
).lower() in {"1", "true", "yes"}
PRIVILEGED_MFA_SESSION_KEY = os.environ.get(
    "PRIVILEGED_MFA_SESSION_KEY", "privileged_mfa_verified_at"
)
SENSITIVE_IDENTITY_READ_RATE_LIMIT_PER_MINUTE = int(
    os.environ.get("SENSITIVE_IDENTITY_READ_RATE_LIMIT_PER_MINUTE", "30")
)

SOURCE_FETCH_ALLOWED_HOSTS = os.environ.get("SOURCE_FETCH_ALLOWED_HOSTS", "")
SOURCE_FETCH_ALLOWED_SCHEMES = os.environ.get("SOURCE_FETCH_ALLOWED_SCHEMES", "https")
SOURCE_FETCH_MAX_BYTES = int(os.environ.get("SOURCE_FETCH_MAX_BYTES", str(25 * 1024 * 1024)))
SOURCE_FETCH_MAX_REDIRECTS = int(os.environ.get("SOURCE_FETCH_MAX_REDIRECTS", "3"))
SOURCE_FETCH_TIMEOUT_SECONDS = float(os.environ.get("SOURCE_FETCH_TIMEOUT_SECONDS", "10"))

OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "curriculum-navigator-api")
OTEL_TRACE_CAPTURE = os.environ.get("OTEL_TRACE_CAPTURE", "false").lower() in {
    "1",
    "true",
    "yes",
}
OBSERVABILITY_METRICS_TOKEN = os.environ.get("OBSERVABILITY_METRICS_TOKEN", "")

API_TITLE = "Curriculum Navigator API"
API_VERSION = "1.0.0"
APP_VERSION = "0.1.0"
API_PROBLEM_BASE_URL = os.environ.get(
    "API_PROBLEM_BASE_URL", "https://api.curriculum-navigator.local/problems"
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "modules.observability.logging.JsonFormatter",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
