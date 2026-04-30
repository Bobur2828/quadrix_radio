"""Default Celery beat schedule registered into django-celery-beat.

Idempotent: only inserts entries that don't already exist (matched by `name`).
Triggered on `post_migrate` for the radio app and gated by RADIO_BEAT_ENABLED.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


_SCHEDULE = [
    # name, task, kind, args
    ('radio.update_current_track', 'radio.tasks.current.update_current_track',
     {'interval': 60, 'unit': 'seconds'}),
    ('radio.check_radio_health', 'radio.tasks.health.check_radio_health',
     {'interval': 60, 'unit': 'seconds'}),
    ('radio.cleanup_stale_state', 'radio.tasks.current.cleanup_stale_state',
     {'interval': 30, 'unit': 'minutes'}),
    ('radio.activate_daily_playlists', 'radio.tasks.playlist.activate_daily_playlists',
     {'crontab': {'minute': '5', 'hour': '0'}}),
    ('radio.ensure_tomorrow_placeholder', 'radio.tasks.playlist.ensure_tomorrow_placeholder',
     {'crontab': {'minute': '15', 'hour': '20'}}),

    ('analytics.expire_stale_sessions', 'analytics.tasks.expire_stale_sessions',
     {'interval': 60, 'unit': 'seconds'}),
    ('analytics.aggregate_daily_stats', 'analytics.tasks.aggregate_daily_stats',
     {'crontab': {'minute': '20', 'hour': '0'}}),
    ('analytics.aggregate_track_plays', 'analytics.tasks.aggregate_track_plays',
     {'crontab': {'minute': '30', 'hour': '0'}}),

    ('notifications.dispatch_scheduled_campaigns', 'notifications.tasks.dispatch_scheduled_campaigns',
     {'interval': 60, 'unit': 'seconds'}),

    ('ads.expire_old_ads', 'ads.tasks.expire_old_ads',
     {'interval': 30, 'unit': 'minutes'}),
]


def install_default_schedule(*args, **kwargs):
    if not getattr(settings, 'RADIO_BEAT_ENABLED', True):
        return

    try:
        from django_celery_beat.models import (  # noqa: WPS433
            CrontabSchedule, IntervalSchedule, PeriodicTask,
        )
    except Exception as exc:
        logger.warning('django_celery_beat unavailable: %s', exc)
        return

    try:
        for name, task, cfg in _SCHEDULE:
            kwargs = {'name': name, 'task': task}
            if 'interval' in cfg:
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=cfg['interval'],
                    period={
                        'seconds': IntervalSchedule.SECONDS,
                        'minutes': IntervalSchedule.MINUTES,
                        'hours': IntervalSchedule.HOURS,
                        'days': IntervalSchedule.DAYS,
                    }[cfg['unit']],
                )
                kwargs['interval'] = interval
                kwargs['crontab'] = None
            elif 'crontab' in cfg:
                ct = cfg['crontab']
                schedule, _ = CrontabSchedule.objects.get_or_create(
                    minute=ct.get('minute', '*'),
                    hour=ct.get('hour', '*'),
                    day_of_week=ct.get('day_of_week', '*'),
                    day_of_month=ct.get('day_of_month', '*'),
                    month_of_year=ct.get('month_of_year', '*'),
                )
                kwargs['crontab'] = schedule
                kwargs['interval'] = None
            else:
                continue

            PeriodicTask.objects.update_or_create(
                name=name, defaults=kwargs,
            )
    except (OperationalError, ProgrammingError) as exc:
        # Tables not yet created (very first migrate). Re-run after migrate.
        logger.info('Beat schedule install deferred: %s', exc)
