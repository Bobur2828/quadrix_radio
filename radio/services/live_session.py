"""DJ live broadcast → MP3 transcoder.

Wraps an ffmpeg subprocess that ingests browser MediaRecorder output
(WebM/Opus or audio/mp4) on stdin and produces a continuous MP3 stream
on stdout. The broadcaster hooks into stdout when a session is live and
forwards those frames to listeners instead of the playlist track.

Lifecycle
---------
1. DJ POSTs `/api/radio/dj/live/start/` → LiveBroadcast row created,
   `stream_key` returned to the browser.
2. Browser starts MediaRecorder (250 ms chunks) and POSTs each chunk
   to `/api/radio/dj/live/<id>/upload/` with `X-Stream-Key` header.
   First POST creates the LiveSession (boots ffmpeg) and attaches it
   to the broadcaster for that station.
3. Each subsequent chunk is written to ffmpeg.stdin.
4. Broadcaster's producer thread switches into `live` mode: it reads
   ffmpeg.stdout and pushes those bytes to listener queues.
5. DJ POSTs `/api/radio/dj/live/<id>/stop/` → ffmpeg stdin is closed,
   ffmpeg drains, broadcaster falls back to playlist.

A 15-second watchdog auto-ends the broadcast if no chunk arrives
(DJ closed the tab without clicking Stop).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Auto-end if no chunk arrives within this many seconds.
WATCHDOG_TIMEOUT = 15.0


def _ffmpeg_path() -> str:
    candidates = [
        Path(__file__).resolve().parents[2] / 'venv' / 'bin' / 'ffmpeg',
        Path(shutil.which('ffmpeg') or ''),
    ]
    for c in candidates:
        if c and c.exists():
            return str(c)
    return ''


class LiveSession:
    """One live mic session backed by an ffmpeg subprocess."""

    def __init__(self, broadcast_id: int, input_format: str = 'webm',
                 bitrate: str = '128k'):
        self.broadcast_id = broadcast_id
        self.input_format = input_format
        self.bitrate = bitrate
        self.proc: Optional[subprocess.Popen] = None
        self.last_chunk_at = time.monotonic()
        self.bytes_in = 0
        self.bytes_out = 0
        self._stdin_lock = threading.Lock()
        self._stopping = threading.Event()

    # ---------- lifecycle ----------

    def start(self) -> bool:
        ffmpeg = _ffmpeg_path()
        if not ffmpeg:
            logger.error('ffmpeg binary not found — cannot start LiveSession')
            return False

        # Low-latency ffmpeg: no input probing/analysis, no buffering, push
        # MP3 frames out as soon as they're encoded. Cuts end-to-end DJ→listener
        # latency to ~300-500 ms server-side (browser audio buffer adds more).
        cmd = [
            ffmpeg,
            '-hide_banner', '-loglevel', 'warning',
            '-fflags', 'nobuffer+flush_packets',
            '-flags', 'low_delay',
            '-probesize', '32',
            '-analyzeduration', '0',
            '-thread_queue_size', '512',
            '-f', self.input_format,
            '-i', 'pipe:0',
            '-vn',
            '-c:a', 'libmp3lame',
            '-b:a', self.bitrate,
            '-ar', '44100',
            '-ac', '2',
            '-reservoir', '0',
            '-flush_packets', '1',
            '-f', 'mp3',
            'pipe:1',
        ]
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except OSError as exc:
            logger.error('Failed to spawn ffmpeg: %s', exc)
            return False

        logger.info('LiveSession[%s] started (pid=%s, fmt=%s)',
                    self.broadcast_id, self.proc.pid, self.input_format)
        return True

    def feed(self, chunk: bytes) -> bool:
        if not chunk or self._stopping.is_set():
            return False
        if not self.proc or self.proc.poll() is not None:
            return False
        with self._stdin_lock:
            try:
                self.proc.stdin.write(chunk)
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                logger.warning('LiveSession[%s] stdin write failed: %s',
                               self.broadcast_id, exc)
                return False
        self.last_chunk_at = time.monotonic()
        self.bytes_in += len(chunk)
        return True

    def read_output(self, max_bytes: int = 1024) -> bytes:
        """Blocking read of MP3 bytes from ffmpeg's stdout.

        Smaller max_bytes (1 KB ≈ 60 ms at 128 kbps) → lower latency.
        """
        if not self.proc or not self.proc.stdout:
            return b''
        try:
            data = self.proc.stdout.read(max_bytes)
        except (OSError, ValueError):
            return b''
        if data:
            self.bytes_out += len(data)
        return data

    def is_alive(self) -> bool:
        if self._stopping.is_set():
            return False
        if not self.proc or self.proc.poll() is not None:
            return False
        return True

    def is_stale(self) -> bool:
        return (time.monotonic() - self.last_chunk_at) > WATCHDOG_TIMEOUT

    def stop(self) -> None:
        self._stopping.set()
        if not self.proc:
            return
        try:
            with self._stdin_lock:
                try:
                    self.proc.stdin.close()
                except Exception:
                    pass
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=1)
        except Exception as exc:
            logger.warning('LiveSession[%s] stop error: %s', self.broadcast_id, exc)
        finally:
            try:
                if self.proc.stdout:
                    self.proc.stdout.close()
            except Exception:
                pass
            logger.info('LiveSession[%s] stopped (in=%d B, out=%d B)',
                        self.broadcast_id, self.bytes_in, self.bytes_out)


# ---------- registry ----------

_REGISTRY: dict[int, LiveSession] = {}
_REGISTRY_LOCK = threading.Lock()


def get(broadcast_id: int) -> Optional[LiveSession]:
    with _REGISTRY_LOCK:
        return _REGISTRY.get(broadcast_id)


def get_or_create(broadcast_id: int, input_format: str = 'webm',
                  bitrate: str = '128k') -> Optional[LiveSession]:
    with _REGISTRY_LOCK:
        sess = _REGISTRY.get(broadcast_id)
        if sess is not None and sess.is_alive():
            return sess
        sess = LiveSession(broadcast_id, input_format=input_format, bitrate=bitrate)
        if not sess.start():
            return None
        _REGISTRY[broadcast_id] = sess
        return sess


def remove(broadcast_id: int) -> Optional[LiveSession]:
    with _REGISTRY_LOCK:
        return _REGISTRY.pop(broadcast_id, None)


def all_sessions() -> list[LiveSession]:
    with _REGISTRY_LOCK:
        return list(_REGISTRY.values())
