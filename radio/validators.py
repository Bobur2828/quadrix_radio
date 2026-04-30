import os

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_audio_extension(file):
    name = getattr(file, 'name', '')
    ext = os.path.splitext(name)[1].lower()
    allowed = settings.RADIO_AUDIO_ALLOWED_EXTS
    if ext not in allowed:
        raise ValidationError(
            f"Audio kengaytmasi qo'llab-quvvatlanmaydi: {ext or '<nomalum>'}. "
            f"Ruxsat etilgan: {', '.join(allowed)}"
        )


def validate_audio_size(file):
    size = getattr(file, 'size', None)
    if size is None:
        return
    if size > settings.RADIO_AUDIO_MAX_BYTES:
        max_mb = settings.RADIO_AUDIO_MAX_BYTES // (1024 * 1024)
        raise ValidationError(f"Audio fayl juda katta: maks. {max_mb} MB")


def validate_audio_file(file):
    validate_audio_extension(file)
    validate_audio_size(file)
