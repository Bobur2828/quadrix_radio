from django.contrib import admin
from unfold.admin import ModelAdmin

from radio.models import StationState


@admin.register(StationState)
class StationStateAdmin(ModelAdmin):
    list_display = (
        'station', 'is_live', 'current_track', 'current_started_at',
        'next_track', 'listeners', 'online', 'last_sync_at',
    )
    list_filter = ('is_live', 'online', 'station')
    readonly_fields = (
        'station', 'current_track', 'current_item',
        'current_started_at', 'current_ends_at',
        'next_track', 'is_live', 'live_broadcast',
        'listeners', 'online', 'last_sync_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
