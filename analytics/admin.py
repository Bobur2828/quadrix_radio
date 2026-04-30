from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from analytics.models import (
    DailyStats, DriverSegment, ListenerEvent, ListenerSession,
    Region, RegionStateMapping, TrackPlayStats,
)


class RegionStateMappingInline(TabularInline):
    model = RegionStateMapping
    extra = 0
    fields = ('state_code',)


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ('code', 'name', 'country', 'timezone', 'is_active', 'sort_order')
    list_filter = ('is_active', 'country')
    search_fields = ('name', 'code')
    inlines = (RegionStateMappingInline,)


@admin.register(DriverSegment)
class DriverSegmentAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class ListenerEventInline(TabularInline):
    model = ListenerEvent
    extra = 0
    can_delete = False
    fields = ('event_type', 'occurred_at', 'track')
    readonly_fields = fields


@admin.register(ListenerSession)
class ListenerSessionAdmin(ModelAdmin):
    list_display = (
        'public_id', 'station', 'platform', 'region', 'segment',
        'started_at', 'ended_at', 'duration_seconds',
    )
    list_filter = ('platform', 'station', 'region', 'segment')
    search_fields = ('device_id', 'public_id', 'ip_address')
    readonly_fields = (
        'public_id', 'station', 'live_broadcast', 'user', 'device_id',
        'platform', 'app_version', 'ip_address', 'user_agent',
        'country', 'state_code', 'region', 'segment',
        'started_at', 'last_heartbeat_at', 'ended_at', 'duration_seconds',
    )
    inlines = (ListenerEventInline,)
    date_hierarchy = 'started_at'

    def has_add_permission(self, request):
        return False


@admin.register(DailyStats)
class DailyStatsAdmin(ModelAdmin):
    list_display = (
        'date', 'station', 'region',
        'sessions_total', 'unique_devices', 'unique_users',
        'listen_seconds', 'peak_concurrent', 'top_track',
    )
    list_filter = ('station', 'region', 'date')
    date_hierarchy = 'date'
    readonly_fields = [f.name for f in DailyStats._meta.fields]


@admin.register(TrackPlayStats)
class TrackPlayStatsAdmin(ModelAdmin):
    list_display = ('date', 'track', 'plays', 'listen_seconds')
    list_filter = ('date',)
    search_fields = ('track__title',)
    date_hierarchy = 'date'
    readonly_fields = [f.name for f in TrackPlayStats._meta.fields]
