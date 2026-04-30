"""Ad lifecycle tasks."""

from __future__ import annotations

from celery import shared_task

from ads.services import scheduler


@shared_task
def expire_old_ads():
    return {'expired': scheduler.burn_out_expired()}
