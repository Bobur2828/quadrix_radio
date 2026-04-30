import logging
import os

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from ads.models import SponsoredAd

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=SponsoredAd)
def fill_ad_metadata(sender, instance: SponsoredAd, **kwargs):
    f = instance.audio_file
    if not f:
        return
    if instance.duration_seconds and instance.file_size:
        return

    try:
        if hasattr(f, 'size') and f.size and not instance.file_size:
            instance.file_size = f.size
    except Exception:
        pass

    try:
        from mutagen import File as MutagenFile  # noqa: WPS433
    except Exception:
        return

    try:
        meta = MutagenFile(f)
        if meta is not None and getattr(meta, 'info', None) is not None:
            info = meta.info
            if not instance.duration_seconds:
                instance.duration_seconds = int(getattr(info, 'length', 0) or 0)
            if not instance.bitrate and getattr(info, 'bitrate', None):
                instance.bitrate = int(info.bitrate // 1000)
    except Exception as exc:
        logger.warning('Could not probe ad audio: %s', exc)
    finally:
        try:
            f.seek(0)
        except Exception:
            pass


@receiver(post_delete, sender=SponsoredAd)
def cleanup_ad_file(sender, instance: SponsoredAd, **kwargs):
    f = instance.audio_file
    if not f:
        return
    try:
        path = f.path
    except Exception:
        return
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError as exc:
            logger.warning('Failed to remove ad file %s: %s', path, exc)
