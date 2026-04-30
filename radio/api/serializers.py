from rest_framework import serializers

from radio.models import (
    AudioTrack, LiveBroadcast, Playlist, PlaylistItem, RadioStation,
)


class TrackPublicSerializer(serializers.ModelSerializer):
    duration = serializers.IntegerField(source='duration_seconds')
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = AudioTrack
        fields = (
            'id', 'title', 'artist', 'duration',
            'category', 'audio_url',
        )

    def get_audio_url(self, obj):
        if not obj.audio_file:
            return None
        request = self.context.get('request')
        url = obj.audio_file.url
        return request.build_absolute_uri(url) if request else url


class PlaylistItemPublicSerializer(serializers.ModelSerializer):
    track = TrackPublicSerializer(read_only=True)

    class Meta:
        model = PlaylistItem
        fields = ('order', 'track', 'planned_start', 'planned_end')


class PlaylistPublicSerializer(serializers.ModelSerializer):
    items = PlaylistItemPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = (
            'id', 'title', 'date', 'station_id',
            'region_id', 'segment_id', 'is_fallback',
            'total_duration', 'items',
        )


class StationPublicSerializer(serializers.ModelSerializer):
    stream_url = serializers.SerializerMethodField()

    class Meta:
        model = RadioStation
        fields = (
            'id', 'name', 'slug', 'description',
            'stream_url', 'bitrate', 'audio_format',
            'is_default', 'is_active', 'is_live',
            'listeners_cached', 'online',
        )

    def get_stream_url(self, obj):
        url = obj.stream_url or ''
        builder = self.context.get('build_absolute_stream_url')
        if builder:
            return builder(url)
        request = self.context.get('request')
        if request and url.startswith('/'):
            return request.build_absolute_uri(url)
        return url


class LivePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveBroadcast
        fields = (
            'id', 'station', 'title', 'description',
            'status', 'started_at', 'ended_at',
            'listener_peak',
        )


class CurrentNowPlayingSerializer(serializers.Serializer):
    is_live = serializers.BooleanField()
    live_title = serializers.CharField(allow_null=True, required=False)
    track_id = serializers.IntegerField(allow_null=True, required=False)
    title = serializers.CharField(allow_blank=True)
    artist = serializers.CharField(allow_blank=True)
    duration = serializers.IntegerField()
    started_at = serializers.CharField(allow_null=True, required=False)
    elapsed = serializers.IntegerField()
    next_track_id = serializers.IntegerField(allow_null=True, required=False)
    next_title = serializers.CharField(allow_null=True, required=False)
    listeners = serializers.IntegerField()
    online = serializers.BooleanField()


class CurrentResponseSerializer(serializers.Serializer):
    stream_url = serializers.URLField()
    is_live = serializers.BooleanField()
    current_track = CurrentNowPlayingSerializer()
    next_track = serializers.DictField(allow_null=True)


class StatusResponseSerializer(serializers.Serializer):
    online = serializers.BooleanField()
    listeners = serializers.IntegerField()
    bitrate = serializers.IntegerField(allow_null=True)
    format = serializers.CharField()
    last_check = serializers.DateTimeField(allow_null=True)
