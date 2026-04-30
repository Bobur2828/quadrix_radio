from django.db import models


class DriverSegment(models.Model):
    """Driver guruhi (cohort): masalan "Long-haul", "Owner-operator", "Team driver".

    Mobile app device registratsiyasida segment yuborilishi mumkin (yoki adminda
    qo'lda biriktiriladi). Playlist va push targeting uchun ishlatiladi.
    """

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('sort_order', 'name')
        verbose_name = 'Driver segment'
        verbose_name_plural = 'Driver segments'

    def __str__(self):
        return self.name
