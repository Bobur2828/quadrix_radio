"""
Celery tasklari uchun joy.

Yangi task yozish:

    @shared_task
    def my_task(arg1, arg2):
        ...
        return result

Taskni chaqirish:

    from main.tasks import my_task
    my_task.delay(1, 2)            # asinxron
    my_task.apply_async((1, 2), countdown=10)  # 10 sekunddan keyin
"""

import logging
import time

from celery import shared_task
from django.db import connection

logger = logging.getLogger(__name__)


@shared_task
def ping_task():
    """Eng oddiy task — Celery worker ishlayotganini tekshirish."""
    return 'pong'


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def add(self, x, y):
    """Misol: ikki sonni qo'shadi. Xato bo'lsa 3 marta qaytadan urinadi."""
    try:
        return x + y
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def run_health_check():
    """
    Barcha komponentlarni tekshirib, natijalarni `HealthCheck` modeliga yozadi.
    """
    from main.models import HealthCheck

    results = []

    # --- Database ---
    start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        results.append(HealthCheck.objects.create(
            component='database',
            status=HealthCheck.Status.OK,
            latency_ms=int((time.perf_counter() - start) * 1000),
        ))
    except Exception as exc:
        logger.exception('DB health check failed')
        results.append(HealthCheck.objects.create(
            component='database',
            status=HealthCheck.Status.DOWN,
            message=str(exc),
        ))

    # --- Redis ---
    start = time.perf_counter()
    try:
        import redis as redis_lib
        from django.conf import settings

        client = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            db=int(settings.REDIS_DB),
            password=settings.REDIS_PASSWORD or None,
            socket_connect_timeout=2,
        )
        client.ping()
        results.append(HealthCheck.objects.create(
            component='redis',
            status=HealthCheck.Status.OK,
            latency_ms=int((time.perf_counter() - start) * 1000),
        ))
    except Exception as exc:
        logger.exception('Redis health check failed')
        results.append(HealthCheck.objects.create(
            component='redis',
            status=HealthCheck.Status.DOWN,
            message=str(exc),
        ))

    return [r.id for r in results]
