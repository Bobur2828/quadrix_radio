"""Recurring radio shows + their weekly schedule.

A `Show` is a named, branded program (e.g. "Morning News", "Night Mix").
Each show has zero or more `ShowSchedule` entries that define WHEN it
airs (day-of-week + time range). When a schedule's slot is active, the
broadcaster prefers the show's playlist over the station's default.
Each airing is recorded as a `ShowEpisode` for analytics and replay.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


def _fmt(t):
    """Render a TimeField value (or its raw string) as HH:MM."""
    if t is None:
        return '--:--'
    if hasattr(t, 'strftime'):
        return t.strftime('%H:%M')
    return str(t)[:5]


class WeekDay(models.IntegerChoices):
    MON = 0, 'Monday'
    TUE = 1, 'Tuesday'
    WED = 2, 'Wednesday'
    THU = 3, 'Thursday'
    FRI = 4, 'Friday'
    SAT = 5, 'Saturday'
    SUN = 6, 'Sunday'


class Show(models.Model):
    """A recurring program with its own playlist + branding."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    cover = models.ImageField(upload_to='radio/shows/', blank=True, null=True)
    color = models.CharField(
        max_length=7, default='#10b981',
        help_text='Hex color for calendar/UI (e.g. #10b981).',
    )

    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='shows'
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='hosted_shows',
    )

    playlist = models.ForeignKey(
        'radio.Playlist',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='shows',
        help_text='Playlist that auto-DJs during the show. If empty, '
                  'the day\'s default playlist plays.',
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('station', 'name')
        verbose_name = 'Show'
        verbose_name_plural = 'Shows'
        indexes = [models.Index(fields=['station', 'is_active'])]

    def __str__(self):
        return f'{self.name} — {self.station.slug}'


class ShowSchedule(models.Model):
    """A weekly time slot for a show (e.g. Mon 09:00–11:00)."""

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='schedules')

    day_of_week = models.IntegerField(choices=WeekDay.choices, db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('day_of_week', 'start_time')
        verbose_name = 'Show schedule'
        verbose_name_plural = 'Show schedules'
        indexes = [
            models.Index(fields=['day_of_week', 'is_active']),
        ]

    def __str__(self):
        d = self.get_day_of_week_display()[:3]
        return f'{self.show.name} • {d} {_fmt(self.start_time)}–{_fmt(self.end_time)}'

    @property
    def crosses_midnight(self) -> bool:
        return self.end_time <= self.start_time


class ShowEpisode(models.Model):
    """One actual airing of a show (created when its slot starts)."""

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='episodes')
    schedule = models.ForeignKey(
        ShowSchedule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='episodes',
    )
    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='show_episodes',
    )
    live_broadcast = models.ForeignKey(
        'radio.LiveBroadcast', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='show_episodes',
        help_text='If a DJ went live during this episode.',
    )

    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    listener_peak = models.PositiveIntegerField(default=0)
    listener_total = models.PositiveIntegerField(default=0)

    recording_path = models.CharField(
        max_length=255, blank=True,
        help_text='Reserved for future recording feature.',
    )

    class Meta:
        ordering = ('-started_at',)
        verbose_name = 'Show episode'
        verbose_name_plural = 'Show episodes'
        indexes = [
            models.Index(fields=['station', '-started_at']),
            models.Index(fields=['ended_at']),
        ]

    def __str__(self):
        return f'{self.show.name} • {self.started_at:%Y-%m-%d %H:%M}'

    @property
    def duration_seconds(self) -> int:
        if not self.ended_at:
            return 0
        return int((self.ended_at - self.started_at).total_seconds())
