from django.conf import settings
from django.db import models


class Platform(models.TextChoices):
    IOS = 'ios', 'iOS'
    ANDROID = 'android', 'Android'
    WEB = 'web', 'Web'


class Device(models.Model):
    """Push uchun ro'yxatdan o'tgan device.

    Mobile app /api/notifications/devices/register/ ga token yuboradi.
    """

    push_token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)

    device_id = models.CharField(max_length=128, blank=True, db_index=True)
    app_version = models.CharField(max_length=32, blank=True)
    locale = models.CharField(max_length=16, blank=True)
    timezone = models.CharField(max_length=64, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='devices',
    )

    region = models.ForeignKey(
        'analytics.Region', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='devices',
    )
    segment = models.ForeignKey(
        'analytics.DriverSegment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='devices',
    )

    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        indexes = [
            models.Index(fields=['platform', 'is_active']),
            models.Index(fields=['region', 'segment', 'is_active']),
        ]

    def __str__(self):
        return f'{self.platform}:{self.push_token[:12]}…'


class CampaignStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    QUEUED = 'queued', 'Queued'
    SENDING = 'sending', 'Sending'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class PushCampaign(models.Model):
    """Adminda yozilgan bitta push xabar (segmentga yoki regionga)."""

    title = models.CharField(max_length=120)
    body = models.TextField()

    payload = models.JSONField(default=dict, blank=True, help_text='deep_link, image_url va h.k.')

    target_region = models.ForeignKey(
        'analytics.Region', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='campaigns',
    )
    target_segment = models.ForeignKey(
        'analytics.DriverSegment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='campaigns',
    )
    target_platform = models.CharField(
        max_length=16, choices=Platform.choices, blank=True,
        help_text='Bo\'sh — barcha platformalarga.',
    )

    scheduled_for = models.DateTimeField(
        null=True, blank=True,
        help_text='Bo\'sh — saqlangach darhol jo\'natiladi.',
    )

    status = models.CharField(
        max_length=16, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT
    )
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='push_campaigns',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Push campaign'
        verbose_name_plural = 'Push campaigns'

    def __str__(self):
        return f'{self.title} [{self.status}]'


class DeliveryStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class PushDelivery(models.Model):
    campaign = models.ForeignKey(
        PushCampaign, on_delete=models.CASCADE, related_name='deliveries'
    )
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name='deliveries'
    )

    status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    error = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=128, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Push delivery'
        verbose_name_plural = 'Push deliveries'
        indexes = [
            models.Index(fields=['campaign', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('campaign', 'device'),
                name='notifications_unique_campaign_device',
            ),
        ]

    def __str__(self):
        return f'{self.campaign.title} → {self.device}'
