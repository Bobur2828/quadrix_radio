from django.contrib import admin, messages
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.decorators import action

from radio.models import LiveBroadcast, LiveStatus, RadioStation


@admin.register(LiveBroadcast)
class LiveBroadcastAdmin(ModelAdmin):
    list_display = (
        'title', 'station', 'status', 'started_at', 'ended_at',
        'listener_peak', 'started_by',
    )
    list_filter = ('status', 'station')
    search_fields = ('title', 'station__name')
    autocomplete_fields = ('station', 'started_by')
    readonly_fields = (
        'stream_key', 'started_at', 'ended_at',
        'listener_peak', 'listener_total',
        'created_at', 'updated_at',
    )

    actions = ('action_start_live', 'action_end_live', 'action_regenerate_key')

    @action(description='Start live broadcast (mark as LIVE)')
    def action_start_live(self, request, queryset):
        started = 0
        for live in queryset:
            if live.status == LiveStatus.LIVE:
                continue
            live.status = LiveStatus.LIVE
            live.started_at = timezone.now()
            live.started_by = request.user
            live.save(update_fields=['status', 'started_at', 'started_by', 'updated_at'])
            RadioStation.objects.filter(pk=live.station_id).update(is_live=True)
            started += 1
        self.message_user(request, f'Started {started} live broadcast(s).', messages.SUCCESS)

    @action(description='End live broadcast')
    def action_end_live(self, request, queryset):
        ended = 0
        for live in queryset.filter(status=LiveStatus.LIVE):
            live.status = LiveStatus.ENDED
            live.ended_at = timezone.now()
            live.save(update_fields=['status', 'ended_at', 'updated_at'])
            RadioStation.objects.filter(pk=live.station_id).update(is_live=False)
            ended += 1
        self.message_user(request, f'Ended {ended} live broadcast(s).', messages.SUCCESS)

    @action(description='Regenerate stream key')
    def action_regenerate_key(self, request, queryset):
        for live in queryset:
            live.regenerate_key()
        self.message_user(request, 'Stream keys regenerated.', messages.SUCCESS)
