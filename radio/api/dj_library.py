"""DJ track library API: browse, search, upload, delete tracks."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.db.models import Q
from django.http import Http404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from radio.models import AudioTrack, TrackCategory, TrackStatus

logger = logging.getLogger(__name__)


_MP3_SIGS = (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2', b'\xff\xfa')


def _is_real_mp3(file_path: str) -> bool:
    try:
        with open(file_path, 'rb') as fh:
            head = fh.read(4)
        return any(head.startswith(s) for s in _MP3_SIGS)
    except OSError:
        return False


def _ffmpeg_path() -> str:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / 'venv' / 'bin' / 'ffmpeg',
        Path(shutil.which('ffmpeg') or ''),
    ]
    for c in candidates:
        if c and c.exists():
            return str(c)
    return ''


def _split_title_artist(stem: str) -> tuple[str, str]:
    for sep in [' - ', ' – ', '_-_', ' — ']:
        if sep in stem:
            artist, title = stem.split(sep, 1)
            return title.strip(), artist.strip()
    return stem.strip(), ''


def _serialize_track(t: AudioTrack, request=None) -> dict:
    audio_url = ''
    if t.audio_file:
        try:
            audio_url = t.audio_file.url
            if request is not None:
                audio_url = request.build_absolute_uri(audio_url)
        except Exception:
            pass
    return {
        'id': t.id,
        'title': t.title,
        'artist': t.artist,
        'description': t.description,
        'duration_seconds': t.duration_seconds,
        'duration_display': t.duration_display,
        'category': t.category,
        'status': t.status,
        'bitrate': t.bitrate,
        'file_size': t.file_size,
        'play_count': t.play_count,
        'last_played_at': t.last_played_at,
        'audio_url': audio_url,
        'created_at': t.created_at,
    }


class TrackLibraryView(APIView):
    """GET/POST /api/radio/dj/library/

    GET parameters: q, category, status, ordering, limit, offset.
    POST: multipart with `audio_file`, optional `title`, `artist`, `category`.
    """
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        qs = AudioTrack.objects.all()
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(artist__icontains=q))
        category = request.GET.get('category', '').strip()
        if category:
            qs = qs.filter(category=category)
        only_status = request.GET.get('status', '').strip()
        if only_status:
            qs = qs.filter(status=only_status)

        ordering = request.GET.get('ordering', '-created_at')
        if ordering not in (
            '-created_at', 'created_at', 'title', '-title',
            'duration_seconds', '-duration_seconds',
            'play_count', '-play_count',
            '-last_played_at', 'last_played_at',
        ):
            ordering = '-created_at'
        qs = qs.order_by(ordering)

        try:
            limit = max(1, min(200, int(request.GET.get('limit', 50))))
            offset = max(0, int(request.GET.get('offset', 0)))
        except ValueError:
            limit, offset = 50, 0

        total = qs.count()
        items = [_serialize_track(t, request=request) for t in qs[offset:offset + limit]]
        return Response({
            'count': total, 'limit': limit, 'offset': offset,
            'results': items,
            'categories': [
                {'value': v, 'label': lbl} for v, lbl in TrackCategory.choices
            ],
        })

    def post(self, request):
        f = request.FILES.get('audio_file')
        if f is None:
            return Response({'detail': 'audio_file is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Save to a temp path so we can probe and possibly transcode.
        tmp_in = Path(tempfile.mkstemp(suffix='_' + f.name)[1])
        try:
            with tmp_in.open('wb') as out:
                for chunk in f.chunks():
                    out.write(chunk)

            ffmpeg = _ffmpeg_path()
            transcoded: Path | None = None
            if not _is_real_mp3(str(tmp_in)) and ffmpeg:
                transcoded = Path(tempfile.mkstemp(suffix='.mp3', prefix='qradio_')[1])
                proc = subprocess.run(
                    [ffmpeg, '-y', '-loglevel', 'error', '-i', str(tmp_in),
                     '-vn', '-c:a', 'libmp3lame', '-b:a', '128k',
                     '-ar', '44100', '-ac', '2', str(transcoded)],
                    capture_output=True, timeout=600,
                )
                if proc.returncode != 0:
                    err = proc.stderr.decode('utf-8', 'ignore').strip()[:300]
                    return Response({'detail': f'transcode failed: {err}'},
                                    status=status.HTTP_400_BAD_REQUEST)
                source_path = transcoded
            else:
                source_path = tmp_in

            stem = os.path.splitext(f.name)[0]
            title_default, artist_default = _split_title_artist(stem)
            title = (request.data.get('title') or title_default).strip()
            artist = (request.data.get('artist') or artist_default or 'Dispatch Radio').strip()
            description = request.data.get('description', '')
            category = request.data.get('category') or TrackCategory.MUSIC
            if category not in dict(TrackCategory.choices):
                category = TrackCategory.MUSIC

            track = AudioTrack(
                title=title, artist=artist, description=description,
                category=category, status=TrackStatus.READY,
                uploaded_by=request.user,
            )
            with source_path.open('rb') as fh:
                track.audio_file.save(stem + '.mp3', File(fh), save=True)
        finally:
            try:
                tmp_in.unlink()
            except OSError:
                pass
            if 'transcoded' in dir() and transcoded and transcoded.exists():
                try:
                    transcoded.unlink()
                except OSError:
                    pass

        return Response(_serialize_track(track, request=request), status=status.HTTP_201_CREATED)


class TrackDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _obj(self, pk):
        try:
            return AudioTrack.objects.get(pk=pk)
        except AudioTrack.DoesNotExist as exc:
            raise Http404 from exc

    def get(self, request, pk):
        return Response(_serialize_track(self._obj(pk), request=request))

    def patch(self, request, pk):
        track = self._obj(pk)
        for field in ('title', 'artist', 'description', 'category', 'status'):
            if field in request.data:
                setattr(track, field, request.data[field])
        track.save()
        return Response(_serialize_track(track, request=request))

    def delete(self, request, pk):
        track = self._obj(pk)
        if track.playlist_items.exists():
            return Response(
                {'detail': 'track is used by a playlist; remove from playlists first.'},
                status=status.HTTP_409_CONFLICT,
            )
        track.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
