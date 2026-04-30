from django.contrib import admin, messages
from unfold.admin import ModelAdmin
from unfold.decorators import action

from notifications.models import (
    CampaignStatus, Device, PushCampaign, PushDelivery,
)


@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    list_display = (
        'short_token', 'platform', 'user', 'region', 'segment',
        'is_active', 'failure_count', 'last_seen_at',
    )
    list_filter = ('platform', 'is_active', 'region', 'segment')
    search_fields = ('push_token', 'device_id', 'user__username')
    autocomplete_fields = ('user', 'region', 'segment')
    readonly_fields = ('last_seen_at', 'failure_count', 'created_at', 'updated_at')

    @admin.display(description='Token', ordering='push_token')
    def short_token(self, obj):
        return f'{obj.push_token[:18]}…'


@admin.register(PushCampaign)
class PushCampaignAdmin(ModelAdmin):
    list_display = (
        'title', 'status', 'target_region', 'target_segment',
        'target_platform', 'sent_count', 'failed_count', 'scheduled_for', 'created_at',
    )
    list_filter = ('status', 'target_platform', 'target_region', 'target_segment')
    search_fields = ('title', 'body')
    autocomplete_fields = ('target_region', 'target_segment')
    readonly_fields = (
        'status', 'sent_count', 'failed_count',
        'started_at', 'finished_at', 'created_at', 'updated_at', 'created_by',
    )

    actions = ('action_queue_send',)

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @action(description='Queue selected campaigns for sending')
    def action_queue_send(self, request, queryset):
        from notifications.tasks import dispatch_campaign

        queued = 0
        for camp in queryset.exclude(status=CampaignStatus.SENDING):
            camp.status = CampaignStatus.QUEUED
            camp.save(update_fields=['status', 'updated_at'])
            dispatch_campaign.delay(camp.id)
            queued += 1
        self.message_user(request, f'Queued {queued} campaign(s).', messages.SUCCESS)


@admin.register(PushDelivery)
class PushDeliveryAdmin(ModelAdmin):
    list_display = ('campaign', 'device', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'campaign')
    search_fields = ('campaign__title', 'device__push_token')
    readonly_fields = [f.name for f in PushDelivery._meta.fields]

    def has_add_permission(self, request):
        return False
