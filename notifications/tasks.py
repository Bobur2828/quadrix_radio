"""Push notification dispatch tasks."""

from __future__ import annotations

import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from notifications.models import (
    CampaignStatus, DeliveryStatus, Device, PushCampaign, PushDelivery,
)
from notifications.services import fcm

logger = logging.getLogger(__name__)


@shared_task
def dispatch_campaign(campaign_id: int):
    """Send a push campaign to all matching devices."""
    try:
        campaign = PushCampaign.objects.get(pk=campaign_id)
    except PushCampaign.DoesNotExist:
        logger.warning('Campaign %s not found', campaign_id)
        return

    if campaign.status == CampaignStatus.SENDING:
        logger.info('Campaign %s already sending', campaign_id)
        return

    campaign.status = CampaignStatus.SENDING
    campaign.started_at = timezone.now()
    campaign.save(update_fields=['status', 'started_at', 'updated_at'])

    qs = Device.objects.filter(is_active=True)
    if campaign.target_region_id:
        qs = qs.filter(Q(region_id=campaign.target_region_id) | Q(region__isnull=True))
    if campaign.target_segment_id:
        qs = qs.filter(Q(segment_id=campaign.target_segment_id) | Q(segment__isnull=True))
    if campaign.target_platform:
        qs = qs.filter(platform=campaign.target_platform)

    sent = 0
    failed = 0
    for device in qs.iterator(chunk_size=200):
        delivery, _ = PushDelivery.objects.get_or_create(
            campaign=campaign, device=device,
        )
        if delivery.status == DeliveryStatus.SENT:
            continue

        result = fcm.send(
            token=device.push_token,
            title=campaign.title,
            body=campaign.body,
            data=campaign.payload or None,
        )

        if result.ok:
            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = timezone.now()
            delivery.provider_message_id = result.message_id
            delivery.error = ''
            delivery.save(update_fields=['status', 'sent_at', 'provider_message_id', 'error'])
            sent += 1
            Device.objects.filter(pk=device.pk).update(
                last_seen_at=timezone.now(), failure_count=0,
            )
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.error = result.error[:500]
            delivery.save(update_fields=['status', 'error'])
            failed += 1
            new_fail = device.failure_count + 1
            updates = {'failure_count': new_fail}
            if new_fail >= 5:
                updates['is_active'] = False
            Device.objects.filter(pk=device.pk).update(**updates)

    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.finished_at = timezone.now()
    if sent and not failed:
        campaign.status = CampaignStatus.SENT
    elif sent:
        campaign.status = CampaignStatus.SENT
    else:
        campaign.status = CampaignStatus.FAILED
    campaign.save(update_fields=[
        'sent_count', 'failed_count', 'finished_at', 'status', 'updated_at',
    ])

    return {'sent': sent, 'failed': failed}


@shared_task
def dispatch_scheduled_campaigns():
    """Pick campaigns whose scheduled_for has passed and queue them."""
    now = timezone.now()
    qs = PushCampaign.objects.filter(
        status=CampaignStatus.DRAFT,
        scheduled_for__isnull=False,
        scheduled_for__lte=now,
    )
    queued = 0
    for camp in qs:
        camp.status = CampaignStatus.QUEUED
        camp.save(update_fields=['status', 'updated_at'])
        dispatch_campaign.delay(camp.id)
        queued += 1
    return {'queued': queued}
