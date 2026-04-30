"""Periodic 'current track' refresher."""

from __future__ import annotations

import logging

from celery import shared_task

from radio.models import RadioStation, StationState
from radio.services import current_track as ct_service

logger = logging.getLogger(__name__)


@shared_task
def update_current_track():
    """Advance StationState for every active station.

    Runs every ~minute. Cheap; bounded by station count.
    """
    advanced = 0
    for station in RadioStation.objects.filter(is_active=True):
        try:
            ct_service.advance_state(station)
            advanced += 1
        except Exception as exc:
            logger.exception('advance_state failed for %s: %s', station.slug, exc)
    return {'advanced': advanced}


@shared_task
def cleanup_stale_state():
    """Reset StationState rows whose current_ends_at is far in the past."""
    from datetime import timedelta
    from django.utils import timezone
    threshold = timezone.now() - timedelta(hours=2)
    n = StationState.objects.filter(current_ends_at__lt=threshold).update(
        current_track=None, current_item=None,
        current_started_at=None, current_ends_at=None,
        next_track=None,
    )
    return {'cleared': n}
