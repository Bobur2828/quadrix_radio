from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import action

from radio.models import RadioStation
from radio.services import icecast


@admin.register(RadioStation)
class RadioStationAdmin(ModelAdmin):
    list_display = (
        'name', 'slug', 'is_default', 'is_active', 'is_live',
        'listeners_cached', 'online_badge', 'updated_at',
    )
    list_filter = ('is_active', 'is_default', 'is_live', 'online')
    search_fields = ('name', 'slug', 'stream_url')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('listeners_cached', 'last_health_check', 'online', 'is_live')

    actions = ('action_ping_icecast',)

    fieldsets = (
        ('Basic', {
            'fields': ('name', 'slug', 'description', 'cover'),
        }),
        ('Stream', {
            'fields': ('stream_url', 'icecast_mount', 'bitrate', 'audio_format'),
        }),
        ('Defaults & fallback', {
            'fields': ('is_default', 'is_active', 'fallback_track'),
        }),
        ('Live state (auto)', {
            'classes': ('collapse',),
            'fields': ('is_live', 'online', 'listeners_cached', 'last_health_check'),
        }),
    )

    @admin.display(description='Online', ordering='online')
    def online_badge(self, obj):
        color = '#10b981' if obj.online else '#ef4444'
        text = 'ONLINE' if obj.online else 'offline'
        return format_html(
            '<span style="color:{};font-weight:600">●</span> {}',
            color, text,
        )

    @action(description='Ping Icecast and refresh listeners')
    def action_ping_icecast(self, request, queryset):
        status = icecast.fetch_status()
        if not status.online:
            self.message_user(
                request,
                f'Icecast unreachable: {status.error or "no sources"}',
                level=messages.ERROR,
            )
            return
        updated = 0
        for station in queryset:
            ms = status.for_mount(station.icecast_mount)
            if ms is None:
                continue
            station.listeners_cached = ms.listeners
            station.online = True
            from django.utils import timezone
            station.last_health_check = timezone.now()
            station.save(update_fields=['listeners_cached', 'online', 'last_health_check'])
            updated += 1
        self.message_user(
            request,
            f'Refreshed {updated} station(s) from Icecast.',
            level=messages.SUCCESS,
        )
