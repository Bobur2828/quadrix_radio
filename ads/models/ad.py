import uuid

from django.conf import settings
from django.db import models

from radio.validators import validate_audio_file


def _ad_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp3'
    return f'ads/audio/{uuid.uuid4().hex}.{ext}'


class AdStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    EXPIRED = 'expired', 'Expired'


class SponsoredAd(models.Model):
    """Reklamali audio (sponsored)."""

    title = models.CharField(max_length=200)
    sponsor = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    audio_file = models.FileField(upload_to=_ad_upload_to, validators=[validate_audio_file])
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size = models.PositiveBigIntegerField(default=0)
    bitrate = models.PositiveIntegerField(null=True, blank=True)

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    max_plays_per_day = models.PositiveIntegerField(
        default=0, help_text='0 — chegarasiz.',
    )
    max_total_plays = models.PositiveIntegerField(default=0, help_text='0 — chegarasiz.')
    weight = models.PositiveSmallIntegerField(
        default=10,
        help_text='Yuqori weight — tez-tez chiqadi (0..100).',
    )

    status = models.CharField(
        max_length=16, choices=AdStatus.choices, default=AdStatus.DRAFT
    )

    target_regions = models.ManyToManyField(
        'analytics.Region', blank=True, related_name='ads',
        help_text='Bo\'sh — barcha regionlar.',
    )
    target_segments = models.ManyToManyField(
        'analytics.DriverSegment', blank=True, related_name='ads',
        help_text='Bo\'sh — barcha driverlar.',
    )

    play_count_total = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_ads',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Sponsored ad'
        verbose_name_plural = 'Sponsored ads'
        indexes = [
            models.Index(fields=['status', 'start_at', 'end_at']),
        ]

    def __str__(self):
        return f'{self.sponsor} — {self.title}'

    @property
    def is_runnable(self) -> bool:
        from django.utils import timezone
        if self.status != AdStatus.ACTIVE:
            return False
        now = timezone.now()
        return self.start_at <= now <= self.end_at
