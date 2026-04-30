"""Pick the right playlist for a (station, region, segment) tuple.

Selection precedence (most-specific wins):
    1. region + segment match
    2. region match (any segment)
    3. segment match (any region)
    4. universal (no region, no segment)
    5. fallback playlist (is_fallback=True)
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Optional

from django.utils import timezone

from radio.models import Playlist, PlaylistStatus, RadioStation


def select_playlist(
    station: RadioStation,
    *,
    day: Optional[date_cls] = None,
    region_id: Optional[int] = None,
    segment_id: Optional[int] = None,
    statuses: tuple = (PlaylistStatus.ACTIVE, PlaylistStatus.SCHEDULED),
    honor_schedule: bool = True,
) -> Optional[Playlist]:
    """Return the most-specific playlist matching the scope, or fallback.

    If `honor_schedule` is True (default) and a show is currently airing on
    this station, that show's playlist takes precedence over the daily one.
    Pass False to bypass the scheduler (used by the scheduler itself when it
    needs to know the underlying default playlist).
    """
    if honor_schedule:
        from radio.services import scheduler as scheduler_service
        show_playlist = scheduler_service.select_show_playlist(station)
        if show_playlist is not None:
            return show_playlist

    day = day or timezone.localdate()

    base_qs = Playlist.objects.filter(
        station=station,
        date=day,
        status__in=statuses,
        is_fallback=False,
    )

    queries = [
        {'region_id': region_id, 'segment_id': segment_id} if region_id and segment_id else None,
        {'region_id': region_id, 'segment_id__isnull': True} if region_id else None,
        {'region_id__isnull': True, 'segment_id': segment_id} if segment_id else None,
        {'region_id__isnull': True, 'segment_id__isnull': True},
    ]

    for q in queries:
        if q is None:
            continue
        pl = base_qs.filter(**q).first()
        if pl is not None:
            return pl

    return (
        Playlist.objects
        .filter(station=station, is_fallback=True)
        .order_by('-date')
        .first()
    )


def serializable_playlist(playlist: Playlist) -> dict:
    """Compact dict for caching / API responses."""
    items = (
        playlist.items
        .select_related('track')
        .filter(is_skipped=False)
        .order_by('order', 'id')
    )
    return {
        'id': playlist.id,
        'title': playlist.title,
        'date': playlist.date.isoformat(),
        'station_id': playlist.station_id,
        'region_id': playlist.region_id,
        'segment_id': playlist.segment_id,
        'is_fallback': playlist.is_fallback,
        'total_duration': playlist.total_duration,
        'items': [
            {
                'order': item.order,
                'track_id': item.track_id,
                'title': item.track.title,
                'artist': item.track.artist,
                'duration': item.track.duration_seconds,
                'category': item.track.category,
                'planned_start': item.planned_start.isoformat() if item.planned_start else None,
            }
            for item in items
        ],
    }
