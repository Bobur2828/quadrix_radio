from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from radio.models import Playlist, PlaylistItem, PlaylistStatus


class PlaylistItemInline(TabularInline):
    model = PlaylistItem
    extra = 0
    autocomplete_fields = ('track',)
    fields = ('order', 'track', 'planned_start', 'planned_end', 'is_skipped', 'note')
    ordering = ('order',)


@admin.register(Playlist)
class PlaylistAdmin(ModelAdmin):
    list_display = (
        'title', 'date', 'station', 'region', 'segment',
        'status', 'is_fallback', 'item_count', 'duration_display',
    )
    list_filter = ('status', 'is_fallback', 'station', 'region', 'segment', 'date')
    search_fields = ('title', 'station__name')
    autocomplete_fields = ('station', 'region', 'segment')
    inlines = (PlaylistItemInline,)
    actions = ('action_activate', 'action_cancel', 'action_clone_for_tomorrow')

    readonly_fields = ('total_duration', 'created_at', 'updated_at')

    @admin.display(description='Items')
    def item_count(self, obj):
        return obj.items.count()

    @admin.display(description='Duration')
    def duration_display(self, obj):
        seconds = int(obj.total_duration or 0)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'

    @action(description='Activate selected playlists')
    def action_activate(self, request, queryset):
        n = queryset.update(status=PlaylistStatus.ACTIVE)
        self.message_user(request, f'Activated {n} playlist(s).', messages.SUCCESS)

    @action(description='Cancel selected playlists')
    def action_cancel(self, request, queryset):
        n = queryset.update(status=PlaylistStatus.CANCELLED)
        self.message_user(request, f'Cancelled {n} playlist(s).', messages.WARNING)

    @action(description='Clone for tomorrow (same items)')
    def action_clone_for_tomorrow(self, request, queryset):
        from datetime import timedelta
        cloned = 0
        for pl in queryset:
            new = Playlist.objects.create(
                title=f'{pl.title} (clone)',
                description=pl.description,
                date=pl.date + timedelta(days=1),
                station=pl.station,
                region=pl.region,
                segment=pl.segment,
                status=PlaylistStatus.SCHEDULED,
                is_fallback=pl.is_fallback,
                auto_repeat=pl.auto_repeat,
                shuffle=pl.shuffle,
            )
            items = [
                PlaylistItem(
                    playlist=new,
                    track=item.track,
                    order=item.order,
                    planned_start=item.planned_start,
                    planned_end=item.planned_end,
                    note=item.note,
                )
                for item in pl.items.all()
            ]
            PlaylistItem.objects.bulk_create(items)
            cloned += 1
        self.message_user(request, f'Cloned {cloned} playlist(s).', messages.SUCCESS)
