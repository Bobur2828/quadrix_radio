"""Auto-populate derived fields and keep state consistent."""

import logging
import os

from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from radio.models import AudioTrack, Playlist, PlaylistItem, RadioStation, StationState

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=AudioTrack)
def fill_audio_metadata(sender, instance: AudioTrack, **kwargs):
    """Yangi yuklangan audio uchun davomiylik, hajm va MIME ni aniqlash."""
    f = instance.audio_file
    if not f:
        return

    needs_probe = not instance.duration_seconds or not instance.file_size
    if not needs_probe:
        return

    try:
        if hasattr(f, 'size') and f.size and not instance.file_size:
            instance.file_size = f.size
    except Exception:
        pass

    try:
        from mutagen import File as MutagenFile  # noqa: WPS433
    except Exception:
        logger.warning('mutagen not installed; cannot probe audio duration')
        return

    try:
        f.open('rb') if hasattr(f, 'open') else None
        meta = MutagenFile(f)
        if meta is not None:
            info = getattr(meta, 'info', None)
            if info is not None:
                if not instance.duration_seconds:
                    instance.duration_seconds = int(getattr(info, 'length', 0) or 0)
                if not instance.bitrate and getattr(info, 'bitrate', None):
                    instance.bitrate = int(info.bitrate // 1000)
                if not instance.sample_rate and getattr(info, 'sample_rate', None):
                    instance.sample_rate = int(info.sample_rate)
            if not instance.mime_type:
                mimes = getattr(meta, 'mime', None)
                if mimes:
                    instance.mime_type = mimes[0]
    except Exception as exc:
        logger.warning('Could not probe audio metadata: %s', exc)
    finally:
        try:
            f.seek(0)
        except Exception:
            pass


@receiver(post_save, sender=RadioStation)
def ensure_station_state(sender, instance: RadioStation, created, **kwargs):
    if created:
        StationState.objects.get_or_create(station=instance)


@receiver([post_save, post_delete], sender=PlaylistItem)
def recalc_playlist_duration(sender, instance: PlaylistItem, **kwargs):
    pl_id = instance.playlist_id
    if not pl_id:
        return

    def _update():
        total = (
            PlaylistItem.objects
            .filter(playlist_id=pl_id, is_skipped=False)
            .aggregate(total=Sum('track__duration_seconds'))
            .get('total')
        ) or 0
        Playlist.objects.filter(pk=pl_id).update(total_duration=total)

    transaction.on_commit(_update)


@receiver(post_delete, sender=AudioTrack)
def cleanup_audio_file(sender, instance: AudioTrack, **kwargs):
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
            logger.warning('Failed to remove audio file %s: %s', path, exc)
