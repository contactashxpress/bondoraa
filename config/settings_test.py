"""
Settings dédiés aux tests (SQLite en mémoire, sans PostgreSQL).
Usage : DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
"""
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DB_NAME", "unused")
os.environ.setdefault("DB_USER", "unused")
os.environ.setdefault("DB_PASSWORD", "unused")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,testserver")
os.environ.setdefault("CSRF_TRUSTED_ORIGINS", "https://bondoraa.com")

from config.settings import *  # noqa: E402,F403

# Désactive l’obligation de libmagic pour les tests unitaires locaux / CI sans libmagic.
FILE_VALIDATION_REQUIRE_MAGIC = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Host utilisé par les tests Client (demande POST).
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, "bondoraa.com", "testserver", "localhost"]))
