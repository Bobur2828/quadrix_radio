import logging.config

from decouple import config
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


# ============================== UNFOLD ADMIN ==============================

UNFOLD = {
    "SITE_TITLE": config('SITE_TITLE', default='Django Base'),
    "SITE_HEADER": config('SITE_HEADER', default='Django Base Admin'),
    "SITE_URL": "/",
    "SITE_SYMBOL": "speed",
}


# ============================== LOGGING ==============================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING)


# ============================== SWAGGER (drf-yasg) ==============================

schema_view = get_schema_view(
    openapi.Info(
        title=config('SITE_TITLE', default='Django Base'),
        default_version='v1',
        description="API documentation",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
