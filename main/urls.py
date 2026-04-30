from django.urls import include, path
from rest_framework.routers import DefaultRouter

from main.views import HealthCheckViewSet, SystemHealthView, TriggerHealthCheckView

router = DefaultRouter()
router.register(r'health-checks', HealthCheckViewSet, basename='health-check')

urlpatterns = [
    path('health/', SystemHealthView.as_view(), name='system-health'),
    path('health/trigger/', TriggerHealthCheckView.as_view(), name='health-trigger'),
    path('', include(router.urls)),
]
