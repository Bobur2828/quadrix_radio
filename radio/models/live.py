import secrets

from django.conf import settings
from django.db import models


class LiveStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    LIVE = 'live', 'Live'
    ENDED = 'ended', 'Ended'
    CANCELLED = 'cancelled', 'Cancelled'


def _generate_stream_key():
    return secrets.token_urlsafe(32)


class LiveBroadcast(models.Model):
    """DJ jonli efir sessiyasi (OBS/BUTT/Mixxx Icecast'ga ulanadi)."""

    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='live_broadcasts'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    stream_key = models.CharField(
        max_length=64, unique=True, default=_generate_stream_key,
        help_text='DJ Icecast\'ga shu kalit bilan ulanadi (sourcepassword).',
    )
    mount_point = models.CharField(
        max_length=64, default='/live',
        help_text='Icecast mount nomi (live efir).',
    )

    status = models.CharField(
        max_length=16, choices=LiveStatus.choices, default=LiveStatus.SCHEDULED
    )

    scheduled_start = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    listener_peak = models.PositiveIntegerField(default=0)
    listener_total = models.PositiveIntegerField(default=0)

    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='live_broadcasts_started',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Live broadcast'
        verbose_name_plural = 'Live broadcasts'
        indexes = [
            models.Index(fields=['station', 'status']),
        ]

    def __str__(self):
        return f'{self.station.name} — {self.title} [{self.status}]'

    def regenerate_key(self):
        self.stream_key = _generate_stream_key()
        self.save(update_fields=['stream_key', 'updated_at'])
