"""Bulk-import audio files from a folder.

Usage:
    python manage.py import_audio mp3/                       # import to default station
    python manage.py import_audio mp3/ --station quadrix
    python manage.py import_audio mp3/ --create-playlist     # also build today's playlist
    python manage.py import_audio mp3/ --activate            # mark playlist ACTIVE
    python manage.py import_audio mp3/ --reset               # purge tracks/playlists first

Each file is copied to MEDIA_ROOT/radio/tracks/. Duration/bitrate are
extracted from MP3 headers via mutagen.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from radio.models import (
    AudioTrack, Playlist, PlaylistItem, PlaylistStatus,
    RadioStation, TrackCategory, TrackStatus,
)


# MP3 magic-byte signatures
_MP3_SIGS = (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2', b'\xff\xfa')


def _is_real_mp3(path: Path) -> bool:
    try:
        with path.open('rb') as fh:
            head = fh.read(4)
        return any(head.startswith(s) for s in _MP3_SIGS)
    except OSError:
        return False


def _ffmpeg_path() -> str:
    """Locate ffmpeg: prefer venv-local, fall back to PATH."""
    candidates = [
        Path(__file__).resolve().parents[3] / 'venv' / 'bin' / 'ffmpeg',
        Path(shutil.which('ffmpeg') or ''),
    ]
    for c in candidates:
        if c and c.exists():
            return str(c)
    return ''


class Command(BaseCommand):
    help = 'Import a folder of audio files into the radio database.'

    def add_arguments(self, parser):
        parser.add_argument('folder', help='Path to folder containing audio files.')
        parser.add_argument('--station', default=None,
                            help='Station slug. Auto-created if missing.')
        parser.add_argument('--station-name', default=None,
                            help='Display name when creating a new station.')
        parser.add_argument('--create-playlist', action='store_true',
                            help='Build today\'s playlist out of imported tracks.')
        parser.add_argument('--activate', action='store_true',
                            help='Set the playlist status to ACTIVE.')
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing tracks + today\'s playlist first.')
        parser.add_argument('--category', default=TrackCategory.MUSIC,
                            help='Track category (default: music).')
        parser.add_argument('--no-transcode', action='store_true',
                            help='Skip ffmpeg conversion (keep file as-is).')
        parser.add_argument('--bitrate', default='128k',
                            help='Target bitrate when transcoding (default: 128k).')

    def handle(self, *args, **opts):
        folder = Path(opts['folder']).expanduser().resolve()
        if not folder.is_dir():
            raise CommandError(f'Folder not found: {folder}')

        station = self._get_station(opts.get('station'),
                                    name_hint=opts.get('station_name'))
        self.stdout.write(self.style.NOTICE(f'Station: {station}'))

        if opts['reset']:
            self._reset(station)

        files = sorted(self._iter_audio_files(folder))
        if not files:
            self.stdout.write(self.style.WARNING('No audio files found.'))
            return

        ffmpeg = '' if opts['no_transcode'] else _ffmpeg_path()
        if not opts['no_transcode'] and not ffmpeg:
            self.stdout.write(self.style.WARNING(
                'ffmpeg not found — files will be imported as-is. Install '
                'ffmpeg or pass --no-transcode to silence this warning.'
            ))

        tracks = []
        skipped = 0
        for path in files:
            try:
                track = self._import_one(path, opts['category'],
                                         ffmpeg=ffmpeg, bitrate=opts['bitrate'])
            except CommandError as exc:
                self.stdout.write(self.style.WARNING(f'  ! skipped {path.name}: {exc}'))
                skipped += 1
                continue
            tracks.append(track)
            self.stdout.write(
                f'  + {track.title}  '
                f'({track.duration_display}, {track.bitrate or "?"} kbps, '
                f'{track.file_size // 1024} KB)'
            )
        if skipped:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped} broken file(s).'))

        self.stdout.write(self.style.SUCCESS(f'Imported {len(tracks)} track(s).'))

        if opts['create_playlist']:
            playlist = self._make_playlist(station, tracks, activate=opts['activate'])
            self.stdout.write(self.style.SUCCESS(
                f'Playlist: {playlist} ({playlist.status})'
            ))

    # ----- helpers -----

    def _get_station(self, slug, *, name_hint=None):
        if slug:
            station = RadioStation.objects.filter(slug=slug).first()
            if station is not None:
                return station
            # Auto-create the named station — first-class multi-station UX.
            return RadioStation.objects.create(
                name=name_hint or slug.replace('-', ' ').replace('_', ' ').title(),
                slug=slug,
                stream_url='/api/radio/stream.mp3',
                is_active=True,
                is_default=not RadioStation.objects.exists(),
            )

        station = RadioStation.objects.filter(is_default=True).first()
        if station is not None:
            return station

        station = RadioStation.objects.first()
        if station is not None:
            return station

        # Bootstrap default station for first-ever import.
        return RadioStation.objects.create(
            name='Quadrix Radio',
            slug='quadrix',
            stream_url='/api/radio/stream.mp3',
            is_default=True,
            is_active=True,
        )

    def _iter_audio_files(self, folder: Path):
        allowed = set(settings.RADIO_AUDIO_ALLOWED_EXTS)
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() in allowed:
                yield entry

    def _reset(self, station):
        deleted_pl, _ = Playlist.objects.filter(station=station).delete()
        # Delete only orphan tracks — ones that no other station's playlist references.
        orphan_tracks = AudioTrack.objects.filter(playlist_items__isnull=True)
        deleted_tr, _ = orphan_tracks.delete()
        self.stdout.write(self.style.WARNING(
            f'Reset {station.slug}: removed {deleted_pl} playlist row(s) and '
            f'{deleted_tr} orphan track(s). Tracks used by other stations are kept.'
        ))

    def _import_one(self, path: Path, category: str, *,
                    ffmpeg: str = '', bitrate: str = '128k') -> AudioTrack:
        title, artist = _split_title_artist(path.stem)
        track = AudioTrack(
            title=title,
            artist=artist or 'Dispatch Radio',
            category=category,
            status=TrackStatus.READY,
        )

        # Always re-encode to MP3 unless the source is already a real MP3 OR
        # transcoding is disabled. This avoids the YouTube-rip trap where a
        # `.mp3` file is actually MP4/WebM and browsers refuse to play it.
        source = path
        tmp_out: Path | None = None
        try:
            if ffmpeg and not _is_real_mp3(path):
                tmp_out = Path(tempfile.mkstemp(suffix='.mp3', prefix='qradio_')[1])
                self._transcode(ffmpeg, path, tmp_out, bitrate)
                source = tmp_out

            target_name = path.stem + '.mp3'  # always .mp3 extension
            with source.open('rb') as fh:
                track.audio_file.save(target_name, File(fh), save=True)
        finally:
            if tmp_out and tmp_out.exists():
                tmp_out.unlink()

        return track

    def _transcode(self, ffmpeg: str, src: Path, dst: Path, bitrate: str):
        """Convert any audio source → MP3 (LAME)."""
        cmd = [
            ffmpeg, '-y', '-loglevel', 'error',
            '-i', str(src),
            '-vn',                       # drop any video
            '-c:a', 'libmp3lame',
            '-b:a', bitrate,
            '-ar', '44100',
            '-ac', '2',
            str(dst),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode('utf-8', 'ignore') if exc.stderr else ''
            raise CommandError(f'ffmpeg failed for {src.name}: {stderr.strip()[:300]}') from exc

    def _make_playlist(self, station, tracks, *, activate: bool):
        today = timezone.localdate()
        title = f'Auto playlist {today.isoformat()}'

        playlist, created = Playlist.objects.update_or_create(
            station=station, date=today, region=None, segment=None,
            defaults={
                'title': title,
                'status': (
                    PlaylistStatus.ACTIVE if activate else PlaylistStatus.SCHEDULED
                ),
            },
        )
        if not created:
            playlist.items.all().delete()

        items = [
            PlaylistItem(playlist=playlist, track=tr, order=i + 1)
            for i, tr in enumerate(tracks)
        ]
        PlaylistItem.objects.bulk_create(items)
        playlist.refresh_from_db()
        return playlist


def _split_title_artist(stem: str) -> tuple[str, str]:
    """Best-effort split of "Artist - Title" filenames."""
    for sep in [' - ', ' – ', '_-_', ' — ']:
        if sep in stem:
            artist, title = stem.split(sep, 1)
            return title.strip(), artist.strip()
    return stem.strip(), ''
