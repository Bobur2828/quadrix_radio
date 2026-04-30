import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ListenerSession(models.Model):
    """Bitta driver tinglash sessiyasi.

    Mobile app /api/analytics/session/ ga `start` yuboradi va keyin
    har 30 sekundda `heartbeat`. `last_heartbeat_at` eskirib qolsa
    `expire_stale_sessions` taski sessiyani yopadi.
    """

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='listener_sessions'
    )
    live_broadcast = models.ForeignKey(
        'radio.LiveBroadcast', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='listener_sessions',
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='listener_sessions',
    )
    device_id = models.CharField(max_length=128, blank=True, db_index=True)
    platform = models.CharField(max_length=16, blank=True, help_text='ios/android/web')
    app_version = models.CharField(max_length=32, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    country = models.CharField(max_length=2, blank=True)
    state_code = models.CharField(max_length=8, blank=True)
    region = models.ForeignKey(
        'analytics.Region', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='listener_sessions',
    )
    segment = models.ForeignKey(
        'analytics.DriverSegment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='listener_sessions',
    )

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_heartbeat_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-started_at',)
        verbose_name = 'Listener session'
        verbose_name_plural = 'Listener sessions'
        indexes = [
            models.Index(fields=['station', '-started_at']),
            models.Index(fields=['ended_at', 'last_heartbeat_at']),
            models.Index(fields=['region', '-started_at']),
        ]

    def __str__(self):
        return f'{self.station.name} | {self.device_id or self.public_id}'

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    def touch(self, *, save: bool = True):
        self.last_heartbeat_at = timezone.now()
        if save:
            self.save(update_fields=['last_heartbeat_at'])

    def end(self, *, save: bool = True):
        now = timezone.now()
        self.ended_at = now
        self.duration_seconds = int((now - self.started_at).total_seconds())
        if save:
            self.save(update_fields=['ended_at', 'duration_seconds'])


class ListenerEvent(models.Model):
    """Sessiya ichidagi muhim hodisalar (track o'tdi, ad eshitildi, error)."""

    class EventType(models.TextChoices):
        START = 'start', 'Start'
        HEARTBEAT = 'heartbeat', 'Heartbeat'
        TRACK_PLAY = 'track_play', 'Track play'
        AD_PLAY = 'ad_play', 'Ad play'
        ERROR = 'error', 'Error'
        END = 'end', 'End'

    session = models.ForeignKey(
        ListenerSession, on_delete=models.CASCADE, related_name='events'
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    track = models.ForeignKey(
        'radio.AudioTrack', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('-occurred_at',)
        verbose_name = 'Listener event'
        verbose_name_plural = 'Listener events'
        indexes = [
            models.Index(fields=['session', '-occurred_at']),
            models.Index(fields=['event_type', '-occurred_at']),
        ]

    def __str__(self):
        return f'{self.event_type} @ {self.occurred_at:%Y-%m-%d %H:%M}'
