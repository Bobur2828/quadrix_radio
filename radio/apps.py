from django.apps import AppConfig


class RadioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'radio'
    verbose_name = 'Radio'

    def ready(self):
        from django.db.models.signals import post_migrate

        from radio import signals  # noqa: F401
        from radio.beat import install_default_schedule

        post_migrate.connect(install_default_schedule, sender=self)
