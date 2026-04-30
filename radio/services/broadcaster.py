"""In-process MP3 broadcaster — a Django-only Icecast substitute.

A single background thread per station reads the playlist in real-time
(throttled to the track's bitrate) and pushes audio chunks to all
subscribed listeners simultaneously. This makes `/stream.mp3` behave
like Icecast: every listener hears the same audio at (approximately)
the same moment, and /current/ stays in sync with the actual playback.

For production with hundreds+ of listeners, switch to Icecast +
Liquidsoap (see deploy/). The broadcaster is fine for local testing
and small deployments (≲ 50 simultaneous listeners per worker).

Threading model
---------------
- One daemon thread per station, started lazily on first subscribe.
- A `threading.Lock` guards the subscriber list.
- Each subscriber owns a bounded `queue.Queue`; slow listeners drop
  chunks rather than block the producer.
- StationState is updated when a track starts so /current/ matches.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from datetime import timedelta
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)

# Per-listener buffer: ~0.2 s worth of 100 ms chunks. Smallest setting that
# absorbs typical TCP jitter; anything tighter and a single stalled listener
# starts dropping audio mid-word. Drop everything on overflow so pause/resume
# jumps to live and slow listeners catch up.
_LISTENER_QUEUE_MAX = 2
_CHUNK_SECONDS = 0.1


class _Broadcaster:
    """Producer thread for one station."""

    def __init__(self, station_id: int):
        self.station_id = station_id
        self.subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()
        self._skip_event = threading.Event()
        self._last_listener_sync = 0.0
        self._last_listener_count = -1
        self._live_session = None  # type: ignore  # LiveSession when DJ is on-air
        self._live_lock = threading.Lock()

    # ----- subscription API -----

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=_LISTENER_QUEUE_MAX)
        with self._lock:
            self.subscribers.append(q)
            if self._thread is None or not self._thread.is_alive():
                self._stopping.clear()
                self._thread = threading.Thread(
                    target=self._run, name=f'radio-broadcaster-{self.station_id}',
                    daemon=True,
                )
                self._thread.start()
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            try:
                self.subscribers.remove(q)
            except ValueError:
                pass

    @property
    def listener_count(self) -> int:
        with self._lock:
            return len(self.subscribers)

    # ----- live (DJ mic) override -----

    def attach_live(self, session) -> None:
        """Switch this station into live (DJ) mode."""
        with self._live_lock:
            self._live_session = session
        # Make sure the producer thread exists even if no one's listening yet.
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._stopping.clear()
                self._thread = threading.Thread(
                    target=self._run, name=f'radio-broadcaster-{self.station_id}',
                    daemon=True,
                )
                self._thread.start()

    def detach_live(self):
        with self._live_lock:
            old, self._live_session = self._live_session, None
        return old

    def is_live(self) -> bool:
        with self._live_lock:
            sess = self._live_session
        return bool(sess and sess.is_alive())

    def skip(self) -> None:
        """Force the producer to abandon the current track and pick the next one."""
        self._skip_event.set()

    # ----- producer loop -----

    def _run(self) -> None:
        from radio.models import RadioStation, StationState
        try:
            station = RadioStation.objects.get(pk=self.station_id)
        except RadioStation.DoesNotExist:
            logger.warning('Broadcaster: station %s gone', self.station_id)
            return

        StationState.objects.update_or_create(station=station, defaults={'online': True})
        logger.info('Broadcaster started for station=%s', station.slug)

        try:
            while not self._stopping.is_set():
                # Live (DJ mic) takes priority over the playlist whenever a
                # LiveSession is attached.
                with self._live_lock:
                    live = self._live_session
                if live is not None and live.is_alive():
                    self._stream_live(station, live)
                    continue

                track = self._pick_next_track(station)
                if track is None:
                    time.sleep(2.0)
                    continue
                self._stream_track(station, track)
        finally:
            StationState.objects.filter(station=station).update(online=False, is_live=False)
            logger.info('Broadcaster stopped for station=%s', station.slug)

    def _stream_live(self, station, live) -> None:
        """Stream the DJ's live mic until the LiveSession is detached or dies."""
        from radio.models import LiveBroadcast, RadioStation, StationState
        from django.utils import timezone

        StationState.objects.filter(station=station).update(
            is_live=True, live_broadcast_id=live.broadcast_id,
            current_track=None, current_item=None,
            current_started_at=timezone.now(), current_ends_at=None,
            last_sync_at=timezone.now(),
        )
        RadioStation.objects.filter(pk=station.pk).update(is_live=True)
        logger.info('Broadcaster[%s] entered LIVE mode (broadcast=%s)',
                    station.slug, live.broadcast_id)

        try:
            while not self._stopping.is_set():
                # Detach if session was swapped out or died (watchdog timeout)
                with self._live_lock:
                    if self._live_session is not live:
                        return
                if not live.is_alive() or live.is_stale():
                    return

                chunk = live.read_output(1024)
                if not chunk:
                    # ffmpeg exited or no data yet
                    if not live.is_alive():
                        return
                    time.sleep(0.05)
                    continue
                self._broadcast(chunk)
        finally:
            StationState.objects.filter(station=station).update(
                is_live=False, live_broadcast=None,
            )
            RadioStation.objects.filter(pk=station.pk).update(is_live=False)
            logger.info('Broadcaster[%s] exited LIVE mode', station.slug)

    # ----- helpers -----

    def _pick_next_track(self, station):
        """Walk the active playlist, looping at the end."""
        from radio.models import PlaylistItem, StationState
        from radio.services import playlist as playlist_service

        pl = playlist_service.select_playlist(station)
        if pl is None:
            return station.fallback_track  # may also be None

        items = list(
            pl.items.select_related('track')
            .filter(is_skipped=False, track__audio_file__isnull=False)
            .order_by('order', 'id')
        )
        # Stream is served as audio/mpeg → only real MP3 files are valid.
        # Skip tracks whose extension isn't .mp3 (m4a/aac/ogg) and tracks
        # whose duration is 0 (mutagen couldn't parse → file is mislabeled
        # or corrupt). Production Liquidsoap transcodes; locally we just filter.
        items = [
            it for it in items
            if str(it.track.audio_file).lower().endswith('.mp3')
            and (it.track.duration_seconds or 0) > 0
        ]
        if not items:
            return station.fallback_track

        state = StationState.objects.filter(station=station).first()
        last_item_id = state.current_item_id if state else None

        next_idx = 0
        if last_item_id:
            for i, it in enumerate(items):
                if it.id == last_item_id:
                    next_idx = (i + 1) % len(items)
                    break

        next_item: PlaylistItem = items[next_idx]
        return self._with_pl_metadata(next_item)

    def _with_pl_metadata(self, item):
        item.track._pl_item_id = item.id  # noqa: SLF001
        return item.track

    def _stream_track(self, station, track):
        from django.db.models import F
        from radio.models import AudioTrack, StationState

        path = self._track_path(track)
        if path is None:
            time.sleep(0.3)
            return

        bitrate_kbps = track.bitrate or station.bitrate or 128
        bytes_per_sec = (bitrate_kbps * 1000) // 8
        chunk_size = max(1024, int(bytes_per_sec * _CHUNK_SECONDS))

        now = timezone.now()
        duration = max(1, int(track.duration_seconds or
                              max(1, os.path.getsize(path) // bytes_per_sec)))
        StationState.objects.filter(station=station).update(
            current_track=track,
            current_item_id=getattr(track, '_pl_item_id', None),
            current_started_at=now,
            current_ends_at=now + timedelta(seconds=duration),
            last_sync_at=now,
        )
        AudioTrack.objects.filter(pk=track.pk).update(
            play_count=F('play_count') + 1, last_played_at=now,
        )
        item_id = getattr(track, '_pl_item_id', None)
        if item_id:
            from radio.models import PlaylistItem
            PlaylistItem.objects.filter(pk=item_id).update(
                play_count=F('play_count') + 1, last_played_at=now,
            )

        try:
            with open(path, 'rb') as fh:
                while not self._stopping.is_set():
                    # DJ pressed Skip → drop the rest of this track immediately.
                    if self._skip_event.is_set():
                        self._skip_event.clear()
                        logger.info('Broadcaster[%s] skipped at user request', self.station_id)
                        return
                    # If a DJ went live mid-track, abandon this file so the
                    # outer _run loop hands control to _stream_live.
                    with self._live_lock:
                        if self._live_session is not None and self._live_session.is_alive():
                            return
                    chunk_start = time.monotonic()
                    chunk = fh.read(chunk_size)
                    if not chunk:
                        return
                    self._broadcast(chunk)
                    elapsed = time.monotonic() - chunk_start
                    if elapsed < _CHUNK_SECONDS:
                        time.sleep(_CHUNK_SECONDS - elapsed)
        except (OSError, FileNotFoundError) as exc:
            logger.warning('Broadcaster: read failed on %s: %s', path, exc)
            time.sleep(0.5)

    def _track_path(self, track) -> Optional[str]:
        try:
            path = track.audio_file.path
            return path if os.path.isfile(path) else None
        except Exception:
            return None

    def _broadcast(self, chunk: bytes) -> None:
        n = self.listener_count
        with self._lock:
            for q in list(self.subscribers):
                try:
                    q.put_nowait(chunk)
                except queue.Full:
                    # Listener fell behind (paused, slow network, or just
                    # disconnected). Drain everything queued so when they
                    # resume reading they get *live* audio, not 4 seconds of
                    # stale buffer.
                    while True:
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            break
                    try:
                        q.put_nowait(chunk)
                    except queue.Full:
                        pass

        # Throttled DB write — SQLite can't take 4/sec, and the value usually
        # doesn't change between chunks anyway.
        from radio.models import StationState
        now = time.monotonic()
        if (now - self._last_listener_sync > 5.0) or n != self._last_listener_count:
            self._last_listener_sync = now
            self._last_listener_count = n
            try:
                StationState.objects.filter(station_id=self.station_id).update(listeners=n)
            except Exception as exc:
                logger.debug('listener-count update skipped: %s', exc)


# ----- module-level registry -----

_INSTANCES: dict[int, _Broadcaster] = {}
_REGISTRY_LOCK = threading.Lock()


def get_for_station(station_id: int) -> _Broadcaster:
    with _REGISTRY_LOCK:
        b = _INSTANCES.get(station_id)
        if b is None:
            b = _Broadcaster(station_id)
            _INSTANCES[station_id] = b
        return b
