from django.db import models


class PlaylistStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SCHEDULED = 'scheduled', 'Scheduled'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class Playlist(models.Model):
    """Bir kunlik (yoki segment/region uchun) playlist."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    date = models.DateField(db_index=True)
    station = models.ForeignKey(
        'radio.RadioStation',
        on_delete=models.CASCADE,
        related_name='playlists',
    )

    region = models.ForeignKey(
        'analytics.Region',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='playlists',
        help_text='Bo\'sh — barcha regionlar uchun.',
    )
    segment = models.ForeignKey(
        'analytics.DriverSegment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='playlists',
        help_text='Bo\'sh — barcha driverlar uchun.',
    )

    status = models.CharField(
        max_length=16, choices=PlaylistStatus.choices, default=PlaylistStatus.DRAFT
    )
    is_fallback = models.BooleanField(
        default=False,
        help_text='Asosiy playlist tugaganda yoki bo\'lmaganda ishlatiladi.',
    )

    auto_repeat = models.BooleanField(
        default=True,
        help_text='Playlist tugagach boshidan loop ketadimi.',
    )
    shuffle = models.BooleanField(default=False)

    total_duration = models.PositiveIntegerField(
        default=0,
        help_text='Avtomatik hisoblanadi (sekund).',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date', '-is_fallback')
        verbose_name = 'Playlist'
        verbose_name_plural = 'Playlists'
        indexes = [
            models.Index(fields=['station', 'date', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('station', 'date', 'region', 'segment'),
                name='radio_unique_playlist_per_scope',
            ),
        ]

    def __str__(self):
        scope = []
        if self.region_id:
            scope.append(self.region.code if hasattr(self.region, 'code') else str(self.region))
        if self.segment_id:
            scope.append(str(self.segment))
        suffix = f" [{' / '.join(scope)}]" if scope else ''
        return f'{self.date} — {self.title}{suffix}'


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name='items'
    )
    track = models.ForeignKey(
        'radio.AudioTrack', on_delete=models.PROTECT, related_name='playlist_items'
    )

    order = models.PositiveIntegerField(default=0, db_index=True)
    planned_start = models.TimeField(null=True, blank=True)
    planned_end = models.TimeField(null=True, blank=True)

    is_skipped = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)

    # Playback tracking (set by broadcaster)
    play_count = models.PositiveIntegerField(default=0)
    last_played_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('order', 'id')
        verbose_name = 'Playlist item'
        verbose_name_plural = 'Playlist items'
        indexes = [
            models.Index(fields=['playlist', 'order']),
        ]

    def __str__(self):
        return f'{self.order:03d}. {self.track.title}'
