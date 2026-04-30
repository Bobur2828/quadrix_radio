from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from ads.models import AdPlacementRule, AdPlay, SponsoredAd


@admin.register(SponsoredAd)
class SponsoredAdAdmin(ModelAdmin):
    list_display = (
        'title', 'sponsor', 'status', 'weight',
        'start_at', 'end_at', 'play_count_total', 'duration_display',
    )
    list_filter = ('status', 'sponsor')
    search_fields = ('title', 'sponsor', 'description')
    autocomplete_fields = ('target_regions', 'target_segments')
    readonly_fields = (
        'duration_seconds', 'file_size', 'bitrate',
        'play_count_total', 'audio_preview',
        'created_at', 'updated_at', 'created_by',
    )
    fieldsets = (
        (None, {'fields': ('title', 'sponsor', 'description')}),
        ('Audio', {'fields': ('audio_file', 'audio_preview',
                              'duration_seconds', 'file_size', 'bitrate')}),
        ('Schedule & caps', {
            'fields': ('start_at', 'end_at',
                       'max_plays_per_day', 'max_total_plays', 'weight', 'status')
        }),
        ('Targeting', {'fields': ('target_regions', 'target_segments')}),
        ('Stats', {
            'classes': ('collapse',),
            'fields': ('play_count_total', 'created_at', 'updated_at', 'created_by'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Length')
    def duration_display(self, obj):
        seconds = int(obj.duration_seconds or 0)
        m, s = divmod(seconds, 60)
        return f'{m}:{s:02d}'

    @admin.display(description='Preview')
    def audio_preview(self, obj):
        if not obj.audio_file:
            return '—'
        return format_html(
            '<audio controls style="width:280px"><source src="{}"></audio>',
            obj.audio_file.url,
        )


@admin.register(AdPlacementRule)
class AdPlacementRuleAdmin(ModelAdmin):
    list_display = (
        'name', 'station', 'every_n_tracks', 'max_consecutive_ads',
        'quiet_hours_start', 'quiet_hours_end', 'is_active', 'priority',
    )
    list_filter = ('station', 'is_active')
    search_fields = ('name', 'station__name')
    autocomplete_fields = ('station',)


@admin.register(AdPlay)
class AdPlayAdmin(ModelAdmin):
    list_display = ('ad', 'station', 'region', 'started_at', 'completed', 'duration_seconds')
    list_filter = ('completed', 'station', 'region')
    search_fields = ('ad__title',)
    date_hierarchy = 'started_at'
    readonly_fields = [f.name for f in AdPlay._meta.fields]

    def has_add_permission(self, request):
        return False
