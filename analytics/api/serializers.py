from rest_framework import serializers

from analytics.models import DailyStats, ListenerSession


class SessionStartSerializer(serializers.Serializer):
    station = serializers.SlugField()
    device_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    platform = serializers.ChoiceField(
        choices=['ios', 'android', 'web'], required=False, allow_blank=True,
    )
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True)
    segment_id = serializers.IntegerField(required=False, allow_null=True)
    region_id = serializers.IntegerField(required=False, allow_null=True)


class SessionPublicSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source='public_id', read_only=True)
    heartbeat_interval = serializers.SerializerMethodField()

    class Meta:
        model = ListenerSession
        fields = (
            'session_id', 'station_id', 'started_at',
            'region_id', 'segment_id',
            'heartbeat_interval',
        )

    def get_heartbeat_interval(self, obj):
        from django.conf import settings
        return settings.LISTENER_HEARTBEAT_INTERVAL


class HeartbeatSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()


class EventSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(
        choices=['track_play', 'ad_play', 'error', 'end'],
    )
    track_id = serializers.IntegerField(required=False, allow_null=True)
    payload = serializers.DictField(required=False)


class DailyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStats
        fields = (
            'date', 'station_id', 'region_id',
            'sessions_total', 'unique_devices', 'unique_users',
            'listen_seconds', 'peak_concurrent', 'avg_session_seconds',
            'top_track_id',
        )
