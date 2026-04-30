from django.db import models


class RadioStation(models.Model):
    """Bitta radio kanal — bittasi default bo'lishi shart."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to='radio/stations/', blank=True, null=True)

    stream_url = models.URLField(
        help_text="Mobile app shu URL'ni ochadi (Icecast mount, masalan https://radio.example.com/stream.mp3).",
    )
    bitrate = models.PositiveSmallIntegerField(default=128, help_text='kbps')
    audio_format = models.CharField(max_length=16, default='mp3')

    is_default = models.BooleanField(
        default=False,
        help_text='Mobile app station tanlamagan bo\'lsa shu kanal beriladi.',
    )
    is_active = models.BooleanField(default=True)
    is_live = models.BooleanField(
        default=False,
        help_text='Hozir jonli efir ketayotganini bildiradi (tizim avtomatik o\'rnatadi).',
    )

    fallback_track = models.ForeignKey(
        'radio.AudioTrack',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fallback_for_stations',
        help_text='Playlist tugab qolsa shu trek loop ketadi.',
    )

    icecast_mount = models.CharField(
        max_length=64,
        default='/stream',
        help_text='Icecast mount nomi (admin status query uchun).',
    )

    listeners_cached = models.PositiveIntegerField(default=0)
    last_health_check = models.DateTimeField(null=True, blank=True)
    online = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-is_default', 'name')
        verbose_name = 'Radio station'
        verbose_name_plural = 'Radio stations'
        constraints = [
            models.UniqueConstraint(
                fields=('is_default',),
                condition=models.Q(is_default=True),
                name='radio_only_one_default_station',
            ),
        ]

    def __str__(self):
        return self.name
