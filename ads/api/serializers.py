from rest_framework import serializers


class AdNextRequestSerializer(serializers.Serializer):
    station = serializers.SlugField()
    region_id = serializers.IntegerField(required=False, allow_null=True)
    segment_id = serializers.IntegerField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)


class AdLogSerializer(serializers.Serializer):
    ad_id = serializers.IntegerField()
    station = serializers.SlugField()
    session_id = serializers.UUIDField(required=False, allow_null=True)
    completed = serializers.BooleanField(required=False, default=False)
    duration_seconds = serializers.IntegerField(required=False, default=0)


class AdPublicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    sponsor = serializers.CharField()
    duration = serializers.IntegerField()
    audio_url = serializers.URLField()
