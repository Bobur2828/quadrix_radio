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
ENABLE_SILK = config('ENABLE_SILK', default=True, cast=bool)
LOGGING_STATUS = config('LOGGING_STATUS', default=True, cast=bool)

UNFOLD = UNFOLD_CONFIG

# ======================================= INSTALLED APPS =======================================

DJANGO_APPS = [
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
]

CUSTOM_APPS = [
    'main',
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
        }
    }

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
