from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from radio.models import AudioTrack


@admin.register(AudioTrack)
class AudioTrackAdmin(ModelAdmin):
    list_display = (
        'title', 'artist', 'category', 'status',
        'duration_display', 'play_count', 'region', 'uploaded_by', 'created_at',
    )
    list_filter = ('status', 'category', 'region')
    search_fields = ('title', 'artist', 'description')
    autocomplete_fields = ('region', 'segments', 'uploaded_by')
    readonly_fields = (
        'duration_seconds', 'duration_display', 'file_size',
        'mime_type', 'sample_rate', 'bitrate',
        'play_count', 'last_played_at',
        'audio_preview',
        'created_at', 'updated_at',
    )

    fieldsets = (
        (None, {
            'fields': ('title', 'artist', 'description'),
        }),
        ('Audio file', {
            'fields': ('audio_file', 'audio_preview',
                       'duration_display', 'file_size', 'bitrate', 'sample_rate', 'mime_type'),
        }),
        ('Classification', {
            'fields': ('category', 'status', 'region', 'segments'),
        }),
        ('Stats', {
            'classes': ('collapse',),
            'fields': ('play_count', 'last_played_at', 'created_at', 'updated_at', 'uploaded_by'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Preview')
    def audio_preview(self, obj):
        if not obj.audio_file:
            return '—'
        return format_html(
            '<audio controls style="width:280px"><source src="{}"></audio>',
            obj.audio_file.url,
        )
