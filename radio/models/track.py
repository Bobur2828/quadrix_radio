import uuid

from django.conf import settings
from django.db import models

from radio.validators import validate_audio_file


def _audio_upload_to(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp3'
    return f'radio/tracks/{uuid.uuid4().hex}.{ext}'


class TrackCategory(models.TextChoices):
    NEWS = 'news', 'News'
    MUSIC = 'music', 'Music'
    TALK = 'talk', 'Talk / Show'
    SAFETY = 'safety', 'Safety / Tips'
    WEATHER = 'weather', 'Weather'
    PROMO = 'promo', 'Station promo'
    JINGLE = 'jingle', 'Jingle / Bumper'
    OTHER = 'other', 'Other'


class TrackStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    READY = 'ready', 'Ready'
    ARCHIVED = 'archived', 'Archived'


class AudioTrack(models.Model):
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200, blank=True, default='Dispatch Radio')
    description = models.TextField(blank=True)

    audio_file = models.FileField(
        upload_to=_audio_upload_to,
        validators=[validate_audio_file],
    )

    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text='Avtomatik aniqlanadi (mutagen orqali).',
    )
    file_size = models.PositiveBigIntegerField(default=0)
    mime_type = models.CharField(max_length=64, blank=True)
    sample_rate = models.PositiveIntegerField(null=True, blank=True)
    bitrate = models.PositiveIntegerField(null=True, blank=True, help_text='kbps')

    category = models.CharField(
        max_length=16, choices=TrackCategory.choices, default=TrackCategory.MUSIC
    )
    status = models.CharField(
        max_length=16, choices=TrackStatus.choices, default=TrackStatus.READY
    )

    region = models.ForeignKey(
        'analytics.Region',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tracks',
        help_text='Faqat shu region uchun. Bo\'sh bo\'lsa — universal.',
    )
    segments = models.ManyToManyField(
        'analytics.DriverSegment',
        blank=True,
        related_name='tracks',
        help_text='Faqat shu segmentlardagi driverlar uchun. Bo\'sh — barchasi.',
    )

    play_count = models.PositiveIntegerField(default=0)
    last_played_at = models.DateTimeField(null=True, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='uploaded_tracks',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Audio track'
        verbose_name_plural = 'Audio tracks'
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['region', 'status']),
        ]

    def __str__(self):
        return self.title

    @property
    def duration_display(self):
        seconds = int(self.duration_seconds or 0)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f'{hours}:{minutes:02d}:{seconds:02d}'
        return f'{minutes}:{seconds:02d}'
