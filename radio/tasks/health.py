"""Probe Icecast and refresh per-station listener counts."""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from radio.models import RadioStation
from radio.services import icecast

logger = logging.getLogger(__name__)


@shared_task
def check_radio_health():
    status = icecast.fetch_status(timeout=2.5)
    now = timezone.now()

    for station in RadioStation.objects.filter(is_active=True):
        ms = status.for_mount(station.icecast_mount)
        listeners = ms.listeners if ms else 0
        online = bool(ms) and status.online
        RadioStation.objects.filter(pk=station.pk).update(
            online=online,
            listeners_cached=listeners,
            last_health_check=now,
        )
        # Mirror to StationState for current API
        from radio.models import StationState
        StationState.objects.filter(station_id=station.pk).update(
            online=online,
            listeners=listeners,
            last_sync_at=now,
        )

    return {
        'icecast_online': status.online,
        'total_listeners': status.total_listeners,
        'mounts': len(status.mounts),
        'error': status.error,
    }
