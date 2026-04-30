"""Show scheduler — picks the active show for a given moment, per station.

Used both by the broadcaster (to override the default playlist while a
show is on the air) and by the periodic Celery task that opens/closes
ShowEpisode rows.
"""

from __future__ import annotations

from datetime import datetime, time as time_cls
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from radio.models import RadioStation, Show, ShowSchedule


def current_schedule(station: RadioStation, *, when: Optional[datetime] = None) -> Optional[ShowSchedule]:
    """Return the ShowSchedule that's airing on `station` right now (or `when`).

    Handles the overnight case: if `end_time <= start_time`, the slot wraps
    past midnight (e.g. 22:00–02:00 ⇒ runs Mon-evening AND Tue-early-morning).
    """
    when = when or timezone.localtime()
    weekday = when.weekday()              # 0=Mon .. 6=Sun
    prev_weekday = (weekday - 1) % 7
    now_t = when.time()

    qs = ShowSchedule.objects.filter(
        is_active=True,
        show__is_active=True,
        show__station=station,
    ).select_related('show')

    # Same-day slots: today, start <= now < end (and not crossing midnight)
    same_day = qs.filter(
        day_of_week=weekday,
        start_time__lte=now_t,
        end_time__gt=now_t,
    ).exclude(start_time__gte=models_F('end_time'))

    # Overnight slots that started yesterday and run past midnight: yesterday's
    # day_of_week, end_time > now_t (we're still before the wrap end), start
    # >= end (so it's a wrap)
    overnight_yesterday = qs.filter(
        day_of_week=prev_weekday,
        end_time__gt=now_t,
        start_time__gte=models_F('end_time'),  # wraps past midnight
    )

    # Overnight slots that started today (after start_time but before midnight)
    overnight_today = qs.filter(
        day_of_week=weekday,
        start_time__lte=now_t,
        start_time__gte=models_F('end_time'),  # wraps past midnight
    )

    return (
        same_day.first()
        or overnight_today.first()
        or overnight_yesterday.first()
    )


def select_show_playlist(station: RadioStation, *, when: Optional[datetime] = None):
    """Return the Show's playlist if a show is currently active and has one."""
    sched = current_schedule(station, when=when)
    if sched is None:
        return None
    return sched.show.playlist  # may still be None → caller falls back


def upcoming_schedules(station: RadioStation, *, limit: int = 6,
                        when: Optional[datetime] = None) -> list[dict]:
    """List the next few schedules across the week (for dashboard "Up next")."""
    when = when or timezone.localtime()

    schedules = list(
        ShowSchedule.objects.filter(
            is_active=True, show__is_active=True, show__station=station,
        ).select_related('show').order_by('day_of_week', 'start_time')
    )
    if not schedules:
        return []

    weekday = when.weekday()
    today_t = when.time()

    def _delta_minutes(s: ShowSchedule) -> int:
        days = (s.day_of_week - weekday) % 7
        if days == 0 and s.start_time <= today_t:
            days = 7
        start_dt = (
            when.replace(hour=s.start_time.hour, minute=s.start_time.minute,
                         second=0, microsecond=0)
        )
        return days * 24 * 60 + int((start_dt - when).total_seconds() / 60)

    schedules.sort(key=_delta_minutes)
    return schedules[:limit]


# Avoid importing F at module load (keeps this file self-contained)
def models_F(field):
    from django.db.models import F
    return F(field)
