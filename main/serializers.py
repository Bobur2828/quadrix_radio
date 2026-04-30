from rest_framework import serializers

from main.models import HealthCheck


class HealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCheck
        fields = ('id', 'component', 'status', 'message', 'latency_ms', 'checked_at')
        read_only_fields = ('id', 'checked_at')


class SystemStatusSerializer(serializers.Serializer):
    """`/health/` endpoint javobi uchun (DB ga yozilmaydi)."""

    status = serializers.CharField()
    components = serializers.DictField(child=serializers.DictField())
    timestamp = serializers.DateTimeField()
