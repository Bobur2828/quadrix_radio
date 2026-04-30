from django.db import models


class AdPlacementRule(models.Model):
    """Qachon va qaysi station'da ad qo'yilishi kerak.

    Misol: "Har 5-trekdan keyin 1 ta ad", yoki "Soat 09:00–10:00 da ko'proq ad".
    """

    name = models.CharField(max_length=120)
    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='ad_rules'
    )

    every_n_tracks = models.PositiveSmallIntegerField(
        default=4, help_text='Har N-trekdan keyin ad chiqaradi.',
    )
    max_consecutive_ads = models.PositiveSmallIntegerField(default=1)

    quiet_hours_start = models.TimeField(
        null=True, blank=True,
        help_text='Shu vaqtdan boshlab ad chiqarilmaydi.',
    )
    quiet_hours_end = models.TimeField(
        null=True, blank=True,
        help_text='Shu vaqtgacha ad chiqarilmaydi.',
    )

    is_active = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(
        default=10,
        help_text='Bir nechta rule mos kelsa — eng yuqori priority oladi.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-priority', 'name')
        verbose_name = 'Ad placement rule'
        verbose_name_plural = 'Ad placement rules'

    def __str__(self):
        return f'{self.station.name} — {self.name}'


class AdPlay(models.Model):
    """Ad eshitilgan voqea (analytics + frequency capping uchun)."""

    ad = models.ForeignKey(
        'ads.SponsoredAd', on_delete=models.CASCADE, related_name='plays'
    )
    station = models.ForeignKey(
        'radio.RadioStation', on_delete=models.CASCADE, related_name='ad_plays'
    )
    session = models.ForeignKey(
        'analytics.ListenerSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ad_plays',
    )

    region = models.ForeignKey(
        'analytics.Region', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ad_plays',
    )

    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed = models.BooleanField(default=False)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-started_at',)
        verbose_name = 'Ad play'
        verbose_name_plural = 'Ad plays'
        indexes = [
            models.Index(fields=['ad', '-started_at']),
            models.Index(fields=['station', '-started_at']),
        ]

    def __str__(self):
        return f'{self.ad.title} @ {self.started_at:%Y-%m-%d %H:%M}'
