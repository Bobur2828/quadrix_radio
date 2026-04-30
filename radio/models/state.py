from django.db import models


class StationState(models.Model):
    """Hozir efirda nima ketayotgani (current track) cache holati.

    Har bir kanal uchun bitta — Liquidsoap orqali yangilanadi yoki
    Celery `update_current_track` task'i playlist asosida hisoblaydi.
    """

    station = models.OneToOneField(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='state'
    )

    current_track = models.ForeignKey(
        'radio.AudioTrack',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    current_item = models.ForeignKey(
        'radio.PlaylistItem',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    current_started_at = models.DateTimeField(null=True, blank=True)
    current_ends_at = models.DateTimeField(null=True, blank=True)

    next_track = models.ForeignKey(
        'radio.AudioTrack',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )

    is_live = models.BooleanField(default=False)
    live_broadcast = models.ForeignKey(
        'radio.LiveBroadcast',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )

    # Currently-active show episode (set by the scheduler task).
    current_show_episode = models.ForeignKey(
        'radio.ShowEpisode',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )

    listeners = models.PositiveIntegerField(default=0)
    online = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Station state'
        verbose_name_plural = 'Station states'

    def __str__(self):
        return f'State of {self.station.name}'
