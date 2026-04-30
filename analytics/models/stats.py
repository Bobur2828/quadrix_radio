from django.db import models


class DailyStats(models.Model):
    """Aggregated kunlik statistika (Celery task hisoblaydi)."""

    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='daily_stats'
    )
    date = models.DateField(db_index=True)
    region = models.ForeignKey(
        'analytics.Region', on_delete=models.CASCADE,
        null=True, blank=True, related_name='daily_stats',
    )

    sessions_total = models.PositiveIntegerField(default=0)
    unique_devices = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    listen_seconds = models.PositiveBigIntegerField(default=0)
    peak_concurrent = models.PositiveIntegerField(default=0)

    avg_session_seconds = models.PositiveIntegerField(default=0)

    top_track = models.ForeignKey(
        'radio.AudioTrack', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date',)
        verbose_name = 'Daily stats'
        verbose_name_plural = 'Daily stats'
        constraints = [
            models.UniqueConstraint(
                fields=('station', 'date', 'region'),
                name='analytics_unique_daily_stats_scope',
            ),
        ]
        indexes = [
            models.Index(fields=['station', '-date']),
        ]

    def __str__(self):
        scope = self.region.code if self.region_id else 'ALL'
        return f'{self.date} {self.station.name} [{scope}]'


class TrackPlayStats(models.Model):
    """Track bo'yicha kunlik aggregat (top tracks uchun)."""

    track = models.ForeignKey(
        'radio.AudioTrack', on_delete=models.CASCADE, related_name='play_stats'
    )
    date = models.DateField(db_index=True)
    plays = models.PositiveIntegerField(default=0)
    listen_seconds = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ('-date', '-plays')
        verbose_name = 'Track play stats'
        verbose_name_plural = 'Track play stats'
        constraints = [
            models.UniqueConstraint(
                fields=('track', 'date'),
                name='analytics_unique_track_day',
            ),
        ]

    def __str__(self):
        return f'{self.date} {self.track.title} ×{self.plays}'
