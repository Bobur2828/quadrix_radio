from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from radio.models import Show, ShowEpisode, ShowSchedule


class ShowScheduleInline(TabularInline):
    model = ShowSchedule
    extra = 0
    fields = ('day_of_week', 'start_time', 'end_time', 'is_active', 'note')
    ordering = ('day_of_week', 'start_time')


@admin.register(Show)
class ShowAdmin(ModelAdmin):
    list_display = ('name', 'station', 'host', 'is_active', 'updated_at')
    list_filter = ('is_active', 'station')
    search_fields = ('name', 'description', 'host__username')
    autocomplete_fields = ('station', 'host', 'playlist')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (ShowScheduleInline,)
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'cover', 'color')}),
        ('Station / Host', {'fields': ('station', 'host', 'playlist')}),
        ('Status', {'fields': ('is_active',)}),
    )


@admin.register(ShowSchedule)
class ShowScheduleAdmin(ModelAdmin):
    list_display = ('show', 'day_of_week', 'start_time', 'end_time', 'is_active')
    list_filter = ('day_of_week', 'is_active', 'show__station')
    search_fields = ('show__name', 'note')
    autocomplete_fields = ('show',)


@admin.register(ShowEpisode)
class ShowEpisodeAdmin(ModelAdmin):
    list_display = ('show', 'station', 'started_at', 'ended_at',
                    'duration_seconds', 'listener_peak')
    list_filter = ('station', 'show')
    search_fields = ('show__name',)
    readonly_fields = [f.name for f in ShowEpisode._meta.fields] + ['duration_seconds']
    date_hierarchy = 'started_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
