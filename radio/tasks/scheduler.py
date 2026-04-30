"""Show-scheduler tick task.

Runs every minute. For each active station, checks if a show should now be
airing. If the active show changed since last tick, opens a new ShowEpisode
(closing the previous one) and tells the broadcaster to skip immediately so
listeners hear the new show right away.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from radio.models import RadioStation, ShowEpisode, StationState
from radio.services import broadcaster as broadcaster_service
from radio.services import scheduler as scheduler_service

logger = logging.getLogger(__name__)


@shared_task
def apply_current_show():
    now = timezone.now()
    changed = 0

    for station in RadioStation.objects.filter(is_active=True):
        sched = scheduler_service.current_schedule(station)
        state = StationState.objects.filter(station=station).first()

        previous_episode: ShowEpisode | None = None
        if state and state.current_show_episode_id:
            previous_episode = ShowEpisode.objects.filter(
                pk=state.current_show_episode_id
            ).first()

        # No show now — close any lingering episode.
        if sched is None:
            if previous_episode and previous_episode.ended_at is None:
                previous_episode.ended_at = now
                previous_episode.save(update_fields=['ended_at'])
                StationState.objects.filter(station=station).update(
                    current_show_episode=None,
                )
                broadcaster_service.get_for_station(station.id).skip()
                changed += 1
                logger.info('Show ended on %s: %s', station.slug,
                            previous_episode.show.name)
            continue

        # A show is scheduled. Is the previous episode still the right one?
        if (previous_episode
                and previous_episode.ended_at is None
                and previous_episode.show_id == sched.show_id
                and previous_episode.schedule_id == sched.id):
            continue  # nothing to do

        # New show starting (or replacing previous) — close & open episodes.
        if previous_episode and previous_episode.ended_at is None:
            previous_episode.ended_at = now
            previous_episode.save(update_fields=['ended_at'])

        episode = ShowEpisode.objects.create(
            show=sched.show,
            schedule=sched,
            station=station,
            started_at=now,
        )
        StationState.objects.filter(station=station).update(
            current_show_episode=episode,
        )
        broadcaster_service.get_for_station(station.id).skip()
        changed += 1
        logger.info('Show started on %s: %s (schedule id=%s)',
                    station.slug, sched.show.name, sched.id)

    return {'changed': changed, 'tick_at': now.isoformat()}
