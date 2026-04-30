from django.db import models


class HealthCheck(models.Model):
    """Tizim holatini tekshirish natijalarini saqlovchi model."""

    class Status(models.TextChoices):
        OK = 'ok', 'OK'
        DEGRADED = 'degraded', 'Degraded'
        DOWN = 'down', 'Down'

    component = models.CharField(max_length=64, help_text="Tekshirilgan komponent (db, redis, celery, ...)")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OK)
    message = models.TextField(blank=True, help_text="Qo'shimcha xabar yoki xatolik matni")
    latency_ms = models.PositiveIntegerField(null=True, blank=True, help_text="Tekshiruv davomiyligi (ms)")
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-checked_at',)
        verbose_name = 'Health Check'
        verbose_name_plural = 'Health Checks'
        indexes = [
            models.Index(fields=['component', '-checked_at']),
        ]

    def __str__(self):
        return f"[{self.checked_at:%Y-%m-%d %H:%M}] {self.component}: {self.status}"
