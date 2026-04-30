"""Listener analytics aggregation tasks."""

from __future__ import annotations

import datetime as dt
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

from analytics.models import (
    DailyStats, ListenerEvent, ListenerSession, TrackPlayStats,
)
from radio.models import RadioStation

logger = logging.getLogger(__name__)


@shared_task
def expire_stale_sessions():
    """Close sessions whose last_heartbeat_at is older than LISTENER_SESSION_TTL."""
    threshold = timezone.now() - timedelta(seconds=settings.LISTENER_SESSION_TTL)
    expired = 0
    for session in ListenerSession.objects.filter(
        ended_at__isnull=True, last_heartbeat_at__lt=threshold,
    ).iterator():
        session.end()
        expired += 1
    if expired:
        logger.info('expire_stale_sessions: closed %d session(s)', expired)
    return {'expired': expired}


@shared_task
def aggregate_daily_stats(date_str: str | None = None):
    """Compute DailyStats for the given date (default: yesterday)."""
    if date_str:
        from datetime import date as date_cls
        target = date_cls.fromisoformat(date_str)
    else:
        target = timezone.localdate() - timedelta(days=1)

    day_start = timezone.make_aware(dt.datetime.combine(target, dt.time.min))
    day_end = day_start + timedelta(days=1)

    written = 0
    for station in RadioStation.objects.filter(is_active=True):
        sessions = ListenerSession.objects.filter(
            station=station,
            started_at__gte=day_start, started_at__lt=day_end,
        )

        # Per-region buckets, plus a "None region" rollup
        region_ids = list(sessions.values_list('region_id', flat=True).distinct())
        if None not in region_ids:
            region_ids.append(None)

        for region_id in region_ids:
            scoped = sessions.filter(region_id=region_id) if region_id else sessions

            agg = scoped.aggregate(
                sessions_total=Count('id'),
                listen=Sum('duration_seconds'),
                unique_devices=Count('device_id', distinct=True),
                unique_users=Count('user_id', distinct=True),
            )
            sessions_total = agg.get('sessions_total') or 0
            if sessions_total == 0:
                continue
            listen = int(agg.get('listen') or 0)
            avg = listen // sessions_total if sessions_total else 0

            top_track = (
                ListenerEvent.objects
                .filter(
                    session__in=scoped,
                    event_type=ListenerEvent.EventType.TRACK_PLAY,
                    track__isnull=False,
                )
                .values('track_id')
                .annotate(n=Count('id'))
                .order_by('-n')
                .first()
            )

            DailyStats.objects.update_or_create(
                station=station, date=target, region_id=region_id,
                defaults={
                    'sessions_total': sessions_total,
                    'unique_devices': agg.get('unique_devices') or 0,
                    'unique_users': agg.get('unique_users') or 0,
                    'listen_seconds': listen,
                    'avg_session_seconds': avg,
                    'top_track_id': top_track['track_id'] if top_track else None,
                    'peak_concurrent': _peak_concurrent(scoped),
                },
            )
            written += 1

    return {'date': target.isoformat(), 'written': written}


def _peak_concurrent(sessions_qs) -> int:
    """Sweep-line peak concurrent listeners for a queryset of sessions."""
    timeline = []
    for s in sessions_qs.values('started_at', 'ended_at', 'last_heartbeat_at'):
        end = s['ended_at'] or s['last_heartbeat_at']
        timeline.append((s['started_at'], 1))
        timeline.append((end, -1))
    timeline.sort()
    peak = 0
    cur = 0
    for _, delta in timeline:
        cur += delta
        peak = max(peak, cur)
    return peak


@shared_task
def aggregate_track_plays(date_str: str | None = None):
    """Per-track play counts for one day."""
    if date_str:
        from datetime import date as date_cls
        target = date_cls.fromisoformat(date_str)
    else:
        target = timezone.localdate() - timedelta(days=1)

    day_start = timezone.make_aware(dt.datetime.combine(target, dt.time.min))
    day_end = day_start + timedelta(days=1)

    rows = (
        ListenerEvent.objects
        .filter(
            event_type=ListenerEvent.EventType.TRACK_PLAY,
            occurred_at__gte=day_start, occurred_at__lt=day_end,
            track__isnull=False,
        )
        .values('track_id')
        .annotate(plays=Count('id'))
    )
    written = 0
    for row in rows:
        TrackPlayStats.objects.update_or_create(
            track_id=row['track_id'], date=target,
            defaults={'plays': row['plays']},
        )
        written += 1
    return {'date': target.isoformat(), 'tracks': written}
