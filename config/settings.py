"""
Django settings for config project — PRODUCTION READY
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ─── BASE ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

# ─── SÉCURITÉ ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'www.bondoraa.com,bondoraa.com').split(',') if h.strip()]

# Origines autorisées pour le contrôle CSRF (Referer / Origin). Doivent correspondre à l’URL
# publique en HTTPS (ex. https://www.bondoraa.com). Ajoutez le hostname du VPS si vous y accédez.
# Variable d’environnement : liste séparée par des virgules.
_csrf_origins = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://www.bondoraa.com,https://bondoraa.com',
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

# Sécurité HTTPS
SECURE_SSL_REDIRECT             = not DEBUG #True
#SECURE_HSTS_SECONDS             = 31536000   # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS  = not DEBUG #True
SECURE_HSTS_PRELOAD             = not DEBUG #True
SECURE_PROXY_SSL_HEADER         = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE           = not DEBUG #True
CSRF_COOKIE_SECURE              = not DEBUG #True
SECURE_BROWSER_XSS_FILTER       = True
SECURE_CONTENT_TYPE_NOSNIFF     = True
X_FRAME_OPTIONS                 = 'DENY'

# Uploads : exiger la détection par magic bytes hors DEBUG (production).
_default_require_magic = 'true' if not DEBUG else 'false'
FILE_VALIDATION_REQUIRE_MAGIC = os.environ.get(
    'FILE_VALIDATION_REQUIRE_MAGIC',
    _default_require_magic,
).lower() == 'true'

# Fichiers jusqu’à 5 Mo par pièce : laisser un peu de marge mémoire côté Django.
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# ─── APPLICATIONS ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'signups',
]

AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ─── MIDDLEWARE ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # servir les statics
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.EmailVerificationRequiredMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ─── TEMPLATES ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── BASE DE DONNÉES (PostgreSQL) ─────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ['DB_NAME'],
        'USER':     os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST':     os.environ.get('DB_HOST', 'localhost'),
        'PORT':     os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'sslmode': os.environ.get('DB_SSLMODE', 'require'),
        },
    }
}

# ─── CACHE (optionnel — Redis recommandé en prod) ──────────────────────────────
# Décommentez si vous installez redis + django-redis
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#     }
# }
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# ─── VALIDATION DES MOTS DE PASSE ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── INTERNATIONALISATION ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr'
TIME_ZONE     = 'Europe/Paris'
USE_I18N      = True
USE_L10N      = True
USE_TZ        = True

LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
    ('es', 'Español'),
    ('de', 'Deutsch'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

# ─── FICHIERS STATIQUES ────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise : compression + cache long terme
STORAGES = {
    # Stockage des fichiers uploadés (FileField, ImageField, etc.)
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    # Fichiers statiques servis via WhiteNoise
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ─── MÉDIAS ───────────────────────────────────────────────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── AUTH ─────────────────────────────────────────────────────────────────────
LOGIN_URL             = 'login'
LOGIN_REDIRECT_URL    = 'home'
LOGOUT_REDIRECT_URL   = 'home'
DEFAULT_AUTO_FIELD    = 'django.db.models.BigAutoField'

# ─── EMAIL ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT          = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS       = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.environ.get('DEFAULT_FROM_EMAIL', 'info@bondoraa.com')

# ─── LOGGING ──────────────────────────────────────────────────────────────────
(BASE_DIR / 'logs').mkdir(exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
    },
}

# ─── URL DU SITE ──────────────────────────────────────────────────────────────
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')