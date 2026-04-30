"""Icecast status query service.

Icecast's `/status-json.xsl` endpoint returns the current state of every
mount point. We use it to report "online?" / "listeners" / current title.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class MountStatus:
    mount: str
    listeners: int = 0
    title: str = ''
    artist: str = ''
    bitrate: Optional[int] = None
    audio_format: str = ''
    server_name: str = ''


@dataclass
class IcecastStatus:
    online: bool = False
    error: str = ''
    total_listeners: int = 0
    mounts: dict = field(default_factory=dict)

    def for_mount(self, mount: str) -> Optional[MountStatus]:
        return self.mounts.get(mount.lstrip('/'))


def _normalize_mount(name: str) -> str:
    return name.lstrip('/')


def fetch_status(timeout: float = 2.0) -> IcecastStatus:
    """Read Icecast public status JSON.

    Doesn't require admin credentials — uses the public endpoint.
    """
    url = f'{settings.ICECAST_PUBLIC_BASE.rstrip("/")}/status-json.xsl'
    status = IcecastStatus()
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        status.error = str(exc)
        logger.warning('Icecast status fetch failed: %s', exc)
        return status

    icestats = (data or {}).get('icestats') or {}
    sources = icestats.get('source') or []

    if isinstance(sources, dict):
        sources = [sources]

    total = 0
    for src in sources:
        listener_url = src.get('listenurl') or ''
        mount = _normalize_mount(listener_url.rsplit('/', 1)[-1] or src.get('server_name', ''))
        listeners = int(src.get('listeners') or 0)
        total += listeners
        status.mounts[mount] = MountStatus(
            mount=mount,
            listeners=listeners,
            title=src.get('title', '') or src.get('yp_currently_playing', ''),
            artist=src.get('artist', ''),
            bitrate=int(src['bitrate']) if src.get('bitrate') else None,
            audio_format=src.get('server_type', '').replace('audio/', '') or 'mp3',
            server_name=src.get('server_name', ''),
        )

    status.online = bool(sources)
    status.total_listeners = total
    return status


def kick_source(mount: str, timeout: float = 2.0) -> bool:
    """Force-disconnect a source on Icecast (admin)."""
    url = f'{settings.ICECAST_PUBLIC_BASE.rstrip("/")}/admin/killsource'
    try:
        resp = requests.get(
            url,
            params={'mount': f'/{mount.lstrip("/")}'},
            auth=(settings.ICECAST_ADMIN_USER, settings.ICECAST_ADMIN_PASSWORD),
            timeout=timeout,
        )
        return resp.status_code == 200
    except Exception as exc:
        logger.warning('Icecast killsource failed: %s', exc)
        return False
