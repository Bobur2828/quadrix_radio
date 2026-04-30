"""Playlist-related Celery tasks."""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from radio.models import Playlist, PlaylistStatus, RadioStation
from radio.services import liquidsoap

logger = logging.getLogger(__name__)


@shared_task
def activate_daily_playlists():
    """Mark today's `scheduled` playlists as `active` and yesterday's as `completed`.

    Runs daily at 00:05 local. Idempotent.
    """
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    with transaction.atomic():
        activated = (
            Playlist.objects
            .filter(date=today, status=PlaylistStatus.SCHEDULED)
            .update(status=PlaylistStatus.ACTIVE)
        )
        completed = (
            Playlist.objects
            .filter(date=yesterday, status=PlaylistStatus.ACTIVE)
            .update(status=PlaylistStatus.COMPLETED)
        )

    for station in RadioStation.objects.filter(is_active=True):
        sync_playlist_to_liquidsoap.delay(station.id)

    logger.info('activate_daily_playlists: activated=%d completed=%d', activated, completed)
    return {'activated': activated, 'completed': completed}


@shared_task
def sync_playlist_to_liquidsoap(station_id: int):
    """Write the active playlist's tracks into the .m3u file Liquidsoap reads."""
    try:
        station = RadioStation.objects.get(pk=station_id, is_active=True)
    except RadioStation.DoesNotExist:
        logger.warning('Station %s not found / inactive', station_id)
        return

    today = timezone.localdate()
    pl = (
        Playlist.objects
        .filter(station=station, date=today,
                status__in=(PlaylistStatus.ACTIVE, PlaylistStatus.SCHEDULED),
                region__isnull=True, segment__isnull=True)
        .first()
    )
    if pl is None:
        pl = (
            Playlist.objects
            .filter(station=station, is_fallback=True)
            .order_by('-date')
            .first()
        )
    if pl is None:
        logger.info('No playlist to sync for station %s', station.slug)
        return

    track_paths = []
    for item in pl.items.select_related('track').filter(is_skipped=False).order_by('order'):
        track = item.track
        if not track or not track.audio_file:
            continue
        try:
            track_paths.append(track.audio_file.path)
        except Exception as exc:
            logger.warning('Track %s: cannot resolve path (%s)', track.id, exc)

    if not track_paths:
        logger.info('Playlist %s has no usable tracks', pl.id)
        return

    path = liquidsoap.write_playlist_file(
        station.slug, track_paths, day=today, symlink_current=True,
    )
    liquidsoap.reload_playlist(station.slug)
    return {'station': station.slug, 'tracks': len(track_paths), 'file': path}


@shared_task
def ensure_tomorrow_placeholder():
    """Create empty SCHEDULED playlists for tomorrow so admins see them.

    Only creates if none exist for that station/date.
    """
    tomorrow = timezone.localdate() + timedelta(days=1)
    created = 0
    for station in RadioStation.objects.filter(is_active=True):
        exists = Playlist.objects.filter(
            station=station, date=tomorrow, region__isnull=True, segment__isnull=True,
        ).exists()
        if exists:
            continue
        Playlist.objects.create(
            station=station,
            date=tomorrow,
            title=f'{station.name} — {tomorrow.isoformat()}',
            status=PlaylistStatus.SCHEDULED,
        )
        created += 1
    return {'created': created}
