import time

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import HealthCheck
from main.serializers import HealthCheckSerializer, SystemStatusSerializer
from main.tasks import ping_task, run_health_check


class HealthCheckViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Saqlangan health check natijalari (faqat o'qish)."""

    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    permission_classes = (AllowAny,)


class SystemHealthView(APIView):
    """
    GET /api/v1/health/
    Hozirgi paytdagi tizim holatini ko'rsatadi: DB, Redis, Celery.
    """

    permission_classes = (AllowAny,)

    def get(self, request):
        components = {
            'database': _check_database(),
            'redis': _check_redis(),
            'celery': _check_celery(),
        }

        overall = 'ok'
        if any(c['status'] == 'down' for c in components.values()):
            overall = 'down'
        elif any(c['status'] == 'degraded' for c in components.values()):
            overall = 'degraded'

        payload = {
            'status': overall,
            'components': components,
            'timestamp': timezone.now(),
        }
        serializer = SystemStatusSerializer(payload)
        http_status = status.HTTP_200_OK if overall == 'ok' else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(serializer.data, status=http_status)


class TriggerHealthCheckView(APIView):
    """
    POST /api/v1/health/trigger/
    Celery taskni ishga tushiradi: u barcha komponentlarni tekshirib, DB ga yozadi.
    """

    permission_classes = (AllowAny,)

    def post(self, request):
        async_result = run_health_check.delay()
        return Response(
            {'task_id': async_result.id, 'status': 'queued'},
            status=status.HTTP_202_ACCEPTED,
        )


# ============================== Helpers ==============================

def _check_database():
    start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        latency = int((time.perf_counter() - start) * 1000)
        return {'status': 'ok', 'latency_ms': latency, 'message': ''}
    except Exception as exc:
        return {'status': 'down', 'latency_ms': None, 'message': str(exc)}


def _check_redis():
    start = time.perf_counter()
    try:
        import redis as redis_lib

        client = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT),
            db=int(settings.REDIS_DB),
            password=settings.REDIS_PASSWORD or None,
            socket_connect_timeout=2,
        )
        client.ping()
        latency = int((time.perf_counter() - start) * 1000)
        return {'status': 'ok', 'latency_ms': latency, 'message': ''}
    except Exception as exc:
        return {'status': 'down', 'latency_ms': None, 'message': str(exc)}


def _check_celery():
    """Workerlarga `ping` yuborib javob kelishini tekshiramiz."""
    start = time.perf_counter()
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.ping(timeout=1.0)
        latency = int((time.perf_counter() - start) * 1000)
        if not replies:
            return {'status': 'degraded', 'latency_ms': latency, 'message': 'No workers responded'}
        return {'status': 'ok', 'latency_ms': latency, 'message': f'{len(replies)} worker(s) online'}
    except Exception as exc:
        return {'status': 'down', 'latency_ms': None, 'message': str(exc)}
