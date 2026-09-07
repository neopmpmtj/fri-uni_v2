"""Production settings — VPS (strict security).

Requires in server .env:
    DATABASE_URL, DJANGO_SECRET_KEY (or SECRET_KEY), ALLOWED_HOSTS
Set SECURE_SSL_REDIRECT=True only after TLS (certbot) is serving 443.
"""

from django.core.exceptions import ImproperlyConfigured

from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = False

if not config("DATABASE_URL", default=""):
    raise ImproperlyConfigured("DATABASE_URL is required in production.")

SECRET_KEY = config("DJANGO_SECRET_KEY", default="") or config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_COOKIES = config("SECURE_COOKIES", default=SECURE_SSL_REDIRECT, cast=bool)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(SECURE_SSL_REDIRECT)
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv(), default="")
