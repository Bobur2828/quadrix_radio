"""Liquidsoap integration.

Liquidsoap reads playlist files from disk and exposes a telnet control
socket where we can push commands like `request.push <uri>` to enqueue a
single track or `playlist.reload` to refresh the file-based queue.

The file format we write is `.m3u` — Liquidsoap accepts it via
`playlist(reload_mode="watch", "/path/to/playlist.m3u")`.
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import date
from typing import Iterable, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _playlist_path(station_slug: str, day: Optional[date] = None) -> str:
    base = settings.LIQUIDSOAP_PLAYLIST_DIR
    os.makedirs(base, exist_ok=True)
    if day is None:
        return os.path.join(base, f'{station_slug}.m3u')
    return os.path.join(base, f'{station_slug}-{day.isoformat()}.m3u')


def write_playlist_file(station_slug: str, track_paths: Iterable[str], *,
                        day: Optional[date] = None,
                        symlink_current: bool = True) -> str:
    """Write an .m3u file Liquidsoap can read.

    Returns the absolute path of the written file.
    """
    paths = [p for p in track_paths if p]
    out = _playlist_path(station_slug, day=day)
    tmp = f'{out}.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write('#EXTM3U\n')
        for p in paths:
            fh.write(p + '\n')
    os.replace(tmp, out)
    logger.info('Wrote Liquidsoap playlist %s (%d items)', out, len(paths))

    if symlink_current and day is not None:
        current = _playlist_path(station_slug, day=None)
        try:
            if os.path.islink(current) or os.path.exists(current):
                os.remove(current)
            os.symlink(out, current)
        except OSError as exc:
            logger.warning('Could not symlink current playlist: %s', exc)

    return out


def send_command(command: str, *, timeout: float = 3.0) -> str:
    """Send a single command to Liquidsoap's telnet server, return its reply."""
    host = settings.LIQUIDSOAP_HOST
    port = int(settings.LIQUIDSOAP_PORT)

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(command.encode('utf-8') + b'\n')
            sock.sendall(b'quit\n')
            data = bytearray()
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data.extend(chunk)
        out = data.decode('utf-8', errors='replace').strip()
        # Liquidsoap appends a trailing "Bye!" — strip it
        return out.rsplit('Bye!', 1)[0].strip()
    except Exception as exc:
        logger.warning('Liquidsoap command failed [%s]: %s', command, exc)
        return ''


def reload_playlist(station_slug: str) -> bool:
    """Tell Liquidsoap to reload the playlist for `station_slug`."""
    reply = send_command(f'{station_slug}.reload')
    return bool(reply)


def request_now_playing(station_slug: str) -> dict:
    """Query Liquidsoap for what's currently playing on a station."""
    raw = send_command(f'{station_slug}.metadata')
    if not raw:
        return {}

    info: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if '=' not in line:
            continue
        key, _, value = line.partition('=')
        info[key.strip()] = value.strip().strip('"')
    return info


def skip(station_slug: str) -> bool:
    return bool(send_command(f'{station_slug}.skip'))
