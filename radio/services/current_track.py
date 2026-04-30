"""Resolve "what's playing right now" on a given station.

Source of truth, in order:
    1. If a LiveBroadcast is in `live` status → live takes over.
    2. Liquidsoap telnet metadata (if reachable) → exact filename / title.
    3. Compute from today's playlist + StationState.current_started_at.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Optional

from django.db.models import F
from django.utils import timezone

from radio.models import (
    AudioTrack, LiveBroadcast, LiveStatus, Playlist, PlaylistItem,
    PlaylistStatus, RadioStation, StationState,
)
from radio.services import liquidsoap, playlist as playlist_service


@dataclass
class NowPlaying:
    is_live: bool = False
    live_title: Optional[str] = None
    track_id: Optional[int] = None
    title: str = ''
    artist: str = ''
    duration: int = 0
    started_at: Optional[str] = None
    elapsed: int = 0
    audio_url: Optional[str] = None
    next_track_id: Optional[int] = None
    next_title: Optional[str] = None
    next_audio_url: Optional[str] = None
    listeners: int = 0
    online: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _track_from_filename(filename: str) -> Optional[AudioTrack]:
    if not filename:
        return None
    base = os.path.basename(filename)
    return (
        AudioTrack.objects
        .filter(audio_file__icontains=base)
        .first()
    )


def resolve_for_station(station: RadioStation, *, region_id: Optional[int] = None,
                        segment_id: Optional[int] = None) -> NowPlaying:
    state, _ = StationState.objects.get_or_create(station=station)

    # Auto-advance if state is empty or expired (Celery beat may not be running
    # locally; this gives a working "radio" purely from Django).
    needs_advance = (
        state.current_item_id is None
        or state.current_ends_at is None
        or state.current_ends_at <= timezone.now()
    )
    if needs_advance:
        try:
            advance_state(station)
            state.refresh_from_db()
        except Exception:
            pass

    np = NowPlaying(
        listeners=state.listeners,
        online=state.online,
    )

    live = (
        LiveBroadcast.objects
        .filter(station=station, status=LiveStatus.LIVE)
        .order_by('-started_at')
        .first()
    )
    if live is not None:
        np.is_live = True
        np.live_title = live.title
        np.title = live.title
        np.artist = 'Live'
        np.started_at = (live.started_at or timezone.now()).isoformat()
        return np

    ls_meta = liquidsoap.request_now_playing(station.slug)
    track: Optional[AudioTrack] = None
    if ls_meta:
        title = ls_meta.get('title') or ''
        artist = ls_meta.get('artist') or ''
        filename = ls_meta.get('filename') or ''
        track = _track_from_filename(filename) if filename else None
        if track:
            np.track_id = track.id
            np.title = track.title
            np.artist = track.artist or artist
            np.duration = track.duration_seconds
        else:
            np.title = title or filename
            np.artist = artist
        np.started_at = (state.current_started_at or timezone.now()).isoformat()
        return _attach_next(np, station, region_id=region_id, segment_id=segment_id, track=track)

    # Fallback: compute from playlist + state
    if state.current_track_id and state.current_started_at:
        track = state.current_track
        np.track_id = track.id
        np.title = track.title
        np.artist = track.artist
        np.duration = track.duration_seconds
        np.audio_url = _track_url(track)
        np.started_at = state.current_started_at.isoformat()
        elapsed = (timezone.now() - state.current_started_at).total_seconds()
        np.elapsed = max(0, int(elapsed))
        return _attach_next(np, station, region_id=region_id, segment_id=segment_id, track=track)

    pl = playlist_service.select_playlist(
        station, region_id=region_id, segment_id=segment_id,
    )
    if pl is not None:
        item = pl.items.select_related('track').filter(is_skipped=False).order_by('order').first()
        if item is not None:
            track = item.track
            np.track_id = track.id
            np.title = track.title
            np.artist = track.artist
            np.duration = track.duration_seconds
            np.audio_url = _track_url(track)

    return _attach_next(np, station, region_id=region_id, segment_id=segment_id, track=track)


def _track_url(track: Optional[AudioTrack]) -> Optional[str]:
    if track is None or not track.audio_file:
        return None
    try:
        return track.audio_file.url
    except Exception:
        return None


def _attach_next(np: NowPlaying, station: RadioStation, *,
                 region_id: Optional[int], segment_id: Optional[int],
                 track: Optional[AudioTrack]) -> NowPlaying:
    pl = playlist_service.select_playlist(
        station, region_id=region_id, segment_id=segment_id,
    )
    if pl is None:
        return np

    items = list(
        pl.items.select_related('track').filter(is_skipped=False).order_by('order', 'id')
    )
    if not items:
        return np

    next_item: Optional[PlaylistItem] = None
    if track is not None:
        for i, it in enumerate(items):
            if it.track_id == track.id and i + 1 < len(items):
                next_item = items[i + 1]
                break

    if next_item is None and len(items) > 0:
        # If we don't know where we are, just preview the first track.
        next_item = items[0]

    if next_item is not None:
        np.next_track_id = next_item.track_id
        np.next_title = next_item.track.title
        np.next_audio_url = _track_url(next_item.track)

    return np


def advance_state(station: RadioStation) -> None:
    """Move StationState to the next track of today's playlist (best-effort).

    Used by the periodic Celery task `update_current_track`.
    """
    state, _ = StationState.objects.get_or_create(station=station)
    now = timezone.now()

    # Honor live mode first
    live = LiveBroadcast.objects.filter(station=station, status=LiveStatus.LIVE).first()
    state.is_live = bool(live)
    state.live_broadcast = live
    if live:
        state.current_track = None
        state.current_item = None
        state.current_started_at = live.started_at
        state.current_ends_at = None
        state.next_track = None
        state.save(update_fields=[
            'is_live', 'live_broadcast', 'current_track', 'current_item',
            'current_started_at', 'current_ends_at', 'next_track', 'last_sync_at',
        ])
        return

    pl = playlist_service.select_playlist(station)
    if pl is None:
        return

    items = list(
        pl.items.select_related('track').filter(is_skipped=False).order_by('order', 'id')
    )
    if not items:
        return

    # If state is empty or expired, start from the top
    if (
        state.current_item_id is None
        or state.current_ends_at is None
        or state.current_ends_at <= now
    ):
        idx = 0
        if state.current_item_id is not None:
            for i, it in enumerate(items):
                if it.id == state.current_item_id and i + 1 < len(items):
                    idx = i + 1
                    break
            else:
                idx = 0  # loop back to start

        next_item = items[idx]
        duration = max(1, next_item.track.duration_seconds or 1)

        state.current_item = next_item
        state.current_track = next_item.track
        state.current_started_at = now
        state.current_ends_at = now + timedelta(seconds=duration)
        state.next_track = items[(idx + 1) % len(items)].track if len(items) > 1 else None
        state.last_sync_at = now
        state.save(update_fields=[
            'current_item', 'current_track', 'current_started_at',
            'current_ends_at', 'next_track', 'last_sync_at',
        ])

        AudioTrack.objects.filter(pk=next_item.track_id).update(
            play_count=F('play_count') + 1,
            last_played_at=now,
        )

        # Mark playlist active
        if pl.status != PlaylistStatus.ACTIVE:
            Playlist.objects.filter(pk=pl.pk).update(status=PlaylistStatus.ACTIVE)
