from django.db import models


class Region(models.Model):
    """Geo-region (US state, custom group, ...).

    Regional playlist va ads targeting uchun ishlatiladi.
    """

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(
        max_length=16, unique=True,
        help_text='Qisqa kod, masalan "US-TX", "MIDWEST".',
    )
    country = models.CharField(max_length=2, default='US')
    timezone = models.CharField(max_length=64, blank=True, default='America/Chicago')

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('sort_order', 'name')
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'

    def __str__(self):
        return f'{self.code} — {self.name}'


class RegionStateMapping(models.Model):
    """US state code → Region. IP→region resolverda ishlatiladi.

    Misol: US-TX state → "South" region, US-CA → "West".
    """

    state_code = models.CharField(
        max_length=8, unique=True,
        help_text='ISO subdivision code (US-TX, US-CA, ...).',
    )
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name='state_mappings'
    )

    class Meta:
        verbose_name = 'Region ↔ state mapping'
        verbose_name_plural = 'Region ↔ state mappings'

    def __str__(self):
        return f'{self.state_code} → {self.region.code}'
