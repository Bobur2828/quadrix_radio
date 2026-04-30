from django.apps import AppConfig


class AdsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ads'
    verbose_name = 'Sponsored Ads'

    def ready(self):
        from ads import signals  # noqa: F401
