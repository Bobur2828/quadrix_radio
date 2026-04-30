import os
from pathlib import Path
from decouple import config, Csv

from config.custom_config import UNFOLD as UNFOLD_CONFIG, setup_logging

# ======================================= BASE SETTINGS =======================================

BASE_DIR = Path(__file__).resolve().parent.parent

SITE_ID = 1

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# ======================================= FEATURE FLAGS =======================================

USE_POSTGRES = config('USE_POSTGRES', default=False, cast=bool)
ENABLE_SILK = config('ENABLE_SILK', default=False, cast=bool)
LOGGING_STATUS = config('LOGGING_STATUS', default=True, cast=bool)

UNFOLD = UNFOLD_CONFIG

# ======================================= INSTALLED APPS =======================================

DJANGO_APPS = [
    # Daphne must come before django.contrib.staticfiles so its `runserver`
    # override wins (gives us native WebSocket support out of the box).
    'daphne',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    # Unfold admin theme
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",

    # API & Documentation
    'rest_framework',
    'drf_yasg',

    # CORS
    'corsheaders',

    # Performance monitoring
    *(["silk"] if ENABLE_SILK else []),

    # Celery
    'django_celery_beat',
    'django_celery_results',

    # WebSocket consumers (low-latency live mic)
    'channels',
]

CUSTOM_APPS = [
    'main',
    'radio',
    'analytics',
    'notifications',
    'ads',
]

INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + CUSTOM_APPS

# ======================================= MIDDLEWARE =======================================

CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    *(["silk.middleware.SilkyMiddleware"] if ENABLE_SILK else []),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ======================================= SILK CONFIGURATION =======================================

SILKY_AUTHENTICATION = True        # Faqat login bo'lganlar kira oladi
SILKY_AUTHORISATION = True         # Faqat staff/superuser ko'ra oladi
SILKY_PYTHON_PROFILER = False      # Python kodini profiling qilish
SILKY_ANALYZE_QUERIES = True       # N+1 va sekin SQL larni aniqlash
SILKY_INTERCEPT_PERCENT = 100      # 100% so'rovlarni yozib borish
SILKY_MAX_REQUEST_BODY_SIZE = 1024 * 128   # Maksimal request hajmi (128KB)
SILKY_MAX_RESPONSE_BODY_SIZE = 1024 * 256  # Maksimal javob hajmi (256KB)
SILKY_MAX_RECORDED_REQUESTS = 10000        # Saqlanadigan so'rovlar soni
SILKY_META = True

# ======================================= URLS & WSGI =======================================

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ======================================= DATABASE =======================================

if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            # WAL + busy_timeout so the streaming-thread doesn't deadlock with
            # request handlers when both touch StationState.
            'OPTIONS': {
                'init_command': (
                    'PRAGMA journal_mode=WAL;'
                    'PRAGMA synchronous=NORMAL;'
                    'PRAGMA busy_timeout=5000;'
                    'PRAGMA temp_store=MEMORY;'
                ),
                'transaction_mode': 'IMMEDIATE',
            },
        }
    }

# ======================================= HTTPS / PROXY =======================================

# When Nginx terminates TLS and proxies to gunicorn over HTTP, Django needs
# this header to know the original request was HTTPS (so redirects, cookies,
# and `request.is_secure()` work).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# CSRF must trust the public origin Django sees behind the proxy.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=Csv(),
)

# Production HTTPS hardening — turned on automatically when DEBUG=False.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# ======================================= AUTHENTICATION =======================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ======================================= INTERNATIONALIZATION =======================================

LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_TZ = True

# ======================================= STATIC & MEDIA FILES =======================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ======================================= DEFAULT SETTINGS =======================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ======================================= LOGGING =======================================

if LOGGING_STATUS:
    setup_logging()

# ======================================= REDIS & CELERY =======================================

REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_DB = config('REDIS_DB', default='0')
REDIS_PASSWORD = config('REDIS_PASSWORD', default='')

_redis_auth = f':{REDIS_PASSWORD}@' if REDIS_PASSWORD else ''
_default_redis_url = f'redis://{_redis_auth}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='') or _default_redis_url
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='') or 'django-db'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60         # 30 daqiqa hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60    # 25 daqiqa soft limit

# Periodik tasklarni Django admin orqali boshqarish (django-celery-beat)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Lokal test uchun: True bo'lsa task'lar darhol bajariladi (worker kerak emas)
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# ======================================= CACHE =======================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': _default_redis_url,
        'KEY_PREFIX': 'qradio',
    }
}

# ======================================= REST FRAMEWORK =======================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('THROTTLE_ANON', default='120/min'),
        'user': config('THROTTLE_USER', default='600/min'),
        'session_heartbeat': config('THROTTLE_HEARTBEAT', default='60/min'),
    },
}

# ======================================= RADIO CONFIGURATION =======================================

# Audio upload limits
RADIO_AUDIO_MAX_BYTES = config('RADIO_AUDIO_MAX_BYTES', default=500 * 1024 * 1024, cast=int)  # 500 MB
RADIO_AUDIO_ALLOWED_EXTS = ('.mp3', '.wav', '.m4a', '.aac', '.ogg')
RADIO_AUDIO_ALLOWED_MIME = (
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav',
    'audio/mp4', 'audio/m4a', 'audio/aac', 'audio/ogg', 'audio/webm',
)

# Cache TTLs (seconds) for hot API endpoints
RADIO_CACHE_TTL_CURRENT = config('RADIO_CACHE_TTL_CURRENT', default=4, cast=int)
RADIO_CACHE_TTL_STATUS = config('RADIO_CACHE_TTL_STATUS', default=8, cast=int)
RADIO_CACHE_TTL_PLAYLIST = config('RADIO_CACHE_TTL_PLAYLIST', default=45, cast=int)

# Icecast (admin / status reading)
ICECAST_HOST = config('ICECAST_HOST', default='127.0.0.1')
ICECAST_PORT = config('ICECAST_PORT', default='8000')
ICECAST_ADMIN_USER = config('ICECAST_ADMIN_USER', default='admin')
ICECAST_ADMIN_PASSWORD = config('ICECAST_ADMIN_PASSWORD', default='hackme')
ICECAST_PUBLIC_BASE = config('ICECAST_PUBLIC_BASE', default='http://localhost:8000')

# Liquidsoap (telnet control + playlist file output)
LIQUIDSOAP_HOST = config('LIQUIDSOAP_HOST', default='127.0.0.1')
LIQUIDSOAP_PORT = config('LIQUIDSOAP_PORT', default='1234', cast=int)
LIQUIDSOAP_PLAYLIST_DIR = config(
    'LIQUIDSOAP_PLAYLIST_DIR',
    default=str(BASE_DIR / 'media' / 'liquidsoap'),
)

# Push notifications (FCM HTTP v1)
FCM_PROJECT_ID = config('FCM_PROJECT_ID', default='')
FCM_SERVICE_ACCOUNT_FILE = config('FCM_SERVICE_ACCOUNT_FILE', default='')

# Apple Push (APNs) — token-based
APNS_KEY_ID = config('APNS_KEY_ID', default='')
APNS_TEAM_ID = config('APNS_TEAM_ID', default='')
APNS_KEY_FILE = config('APNS_KEY_FILE', default='')
APNS_BUNDLE_ID = config('APNS_BUNDLE_ID', default='')
APNS_USE_SANDBOX = config('APNS_USE_SANDBOX', default=True, cast=bool)

# GeoIP (optional). Path to MaxMind GeoLite2-City.mmdb
GEOIP_DATABASE = config('GEOIP_DATABASE', default='')

# Listener session
LISTENER_SESSION_TTL = config('LISTENER_SESSION_TTL', default=180, cast=int)  # seconds w/o heartbeat → ended
LISTENER_HEARTBEAT_INTERVAL = config('LISTENER_HEARTBEAT_INTERVAL', default=30, cast=int)

# Beat schedule (registered programmatically in radio.tasks.beat)
RADIO_BEAT_ENABLED = config('RADIO_BEAT_ENABLED', default=True, cast=bool)


# DRF api_settings caches `REST_FRAMEWORK` on first access. `custom_config.py`
# (imported on line 5) calls drf_yasg.get_schema_view() at import time which
# pulls DRF api_settings before this module finishes executing, so the cache
# is built with an empty user_settings. Reload it now.
try:
    from rest_framework.settings import api_settings as _drf_api_settings  # noqa: E402
    _drf_api_settings.reload()
except Exception:  # pragma: no cover
    pass
