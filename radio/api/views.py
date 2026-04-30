"""Public radio API used by the mobile app."""

from __future__ import annotations

import queue

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, StreamingHttpResponse
from django.utils import timezone
from django.views import View
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.services import geo as geo_service
from radio.api.serializers import (
    CurrentResponseSerializer, LivePublicSerializer,
    PlaylistPublicSerializer, StationPublicSerializer,
    StatusResponseSerializer,
)
from radio.models import LiveBroadcast, LiveStatus, Playlist, RadioStation
from radio.services import broadcaster as broadcaster_service
from radio.services import current_track as ct_service
from radio.services import playlist as playlist_service


def _client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _resolve_station(slug: str | None) -> RadioStation:
    qs = RadioStation.objects.filter(is_active=True)
    if slug:
        try:
            return qs.get(slug=slug)
        except RadioStation.DoesNotExist as exc:
            raise Http404('Station not found') from exc
    station = qs.filter(is_default=True).first() or qs.first()
    if station is None:
        raise Http404('No active radio station configured')
    return station


def _absolute_stream_url(request, station: RadioStation) -> str:
    """If the station's stream_url is a relative path, prefix it with the
    request's scheme+host. Lets local testing use /api/radio/stream.mp3 while
    production keeps the Icecast https URL."""
    url = station.stream_url or ''
    if url.startswith('/'):
        return request.build_absolute_uri(url)
    return url


def _scope_from_request(request, station: RadioStation) -> tuple[int | None, int | None]:
    region_id = request.query_params.get('region_id')
    segment_id = request.query_params.get('segment_id')
    region_id = int(region_id) if region_id and region_id.isdigit() else None
    segment_id = int(segment_id) if segment_id and segment_id.isdigit() else None

    if region_id is None:
        ip = _client_ip(request)
        result = geo_service.resolve(ip)
        if result.region is not None:
            region_id = result.region.id

    return region_id, segment_id


class _AbsoluteStreamMixin:
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['build_absolute_stream_url'] = lambda url: (
            self.request.build_absolute_uri(url) if url.startswith('/') else url
        )
        return ctx


class StationListView(_AbsoluteStreamMixin, generics.ListAPIView):
    """GET /api/radio/stations/  — list all active stations."""
    permission_classes = (AllowAny,)
    serializer_class = StationPublicSerializer
    queryset = RadioStation.objects.filter(is_active=True)


class StationDetailView(_AbsoluteStreamMixin, generics.RetrieveAPIView):
    """GET /api/radio/stations/<slug>/"""
    permission_classes = (AllowAny,)
    serializer_class = StationPublicSerializer
    queryset = RadioStation.objects.filter(is_active=True)
    lookup_field = 'slug'


class CurrentView(APIView):
    """GET /api/radio/current/?station=<slug>

    Mobile app polls this every few seconds to display the now-playing
    overlay. Cached 3–5 s to absorb hammering.
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        slug = request.query_params.get('station')
        station = _resolve_station(slug)
        region_id, segment_id = _scope_from_request(request, station)

        cache_key = f'radio:current:{station.slug}:{region_id or 0}:{segment_id or 0}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        np = ct_service.resolve_for_station(
            station, region_id=region_id, segment_id=segment_id,
        )

        def _abs(url):
            if not url:
                return None
            return request.build_absolute_uri(url)

        data = {
            'stream_url': _absolute_stream_url(request, station),
            'is_live': np.is_live,
            'current_track': {
                'title': np.title,
                'artist': np.artist,
                'duration': np.duration,
                'track_id': np.track_id,
                'started_at': np.started_at,
                'elapsed': np.elapsed,
                'audio_url': _abs(np.audio_url),
            },
            'next_track': (
                {
                    'title': np.next_title,
                    'track_id': np.next_track_id,
                    'audio_url': _abs(np.next_audio_url),
                }
                if np.next_title else None
            ),
            'listeners': np.listeners,
            'online': np.online,
        }
        cache.set(cache_key, data, settings.RADIO_CACHE_TTL_CURRENT)
        return Response(data)


class StatusView(APIView):
    """GET /api/radio/status/?station=<slug>"""
    permission_classes = (AllowAny,)

    def get(self, request):
        slug = request.query_params.get('station')
        station = _resolve_station(slug)
        cache_key = f'radio:status:{station.slug}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = StatusResponseSerializer({
            'online': station.online,
            'listeners': station.listeners_cached,
            'bitrate': station.bitrate,
            'format': station.audio_format,
            'last_check': station.last_health_check,
        }).data

        cache.set(cache_key, data, settings.RADIO_CACHE_TTL_STATUS)
        return Response(data)


class TodayPlaylistView(APIView):
    """GET /api/radio/playlist/today/?station=<slug>"""
    permission_classes = (AllowAny,)

    def get(self, request):
        slug = request.query_params.get('station')
        station = _resolve_station(slug)
        region_id, segment_id = _scope_from_request(request, station)

        cache_key = (
            f'radio:playlist:{station.slug}:'
            f'{timezone.localdate().isoformat()}:'
            f'{region_id or 0}:{segment_id or 0}'
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        playlist = playlist_service.select_playlist(
            station, region_id=region_id, segment_id=segment_id,
        )
        if playlist is None:
            return Response({'detail': 'No playlist scheduled.'},
                            status=status.HTTP_404_NOT_FOUND)

        data = PlaylistPublicSerializer(playlist, context={'request': request}).data
        cache.set(cache_key, data, settings.RADIO_CACHE_TTL_PLAYLIST)
        return Response(data)


class LiveCurrentView(APIView):
    """GET /api/radio/live/?station=<slug>"""
    permission_classes = (AllowAny,)

    def get(self, request):
        slug = request.query_params.get('station')
        station = _resolve_station(slug)
        live = (
            LiveBroadcast.objects
            .filter(station=station, status=LiveStatus.LIVE)
            .order_by('-started_at')
            .first()
        )
        if live is None:
            return Response({'is_live': False})
        data = LivePublicSerializer(live).data
        data['is_live'] = True
        return Response(data)


class TestPlayerView(View):
    """GET /api/radio/test/[?station=<slug>]  — multi-station HTML player."""

    def get(self, request):
        from django.http import HttpResponse
        # Initial slug just hints which station to start on; client-side JS
        # handles all switching after that, no server reload needed.
        initial = request.GET.get('station', '')
        html = TEST_PLAYER_HTML.replace('__INITIAL_SLUG__', initial)
        return HttpResponse(html, content_type='text/html; charset=utf-8')


TEST_PLAYER_HTML = r"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="utf-8">
<title>Quadrix Radio — Test Player</title>
<style>
    body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; margin: 0; padding: 20px; }
    .card { background: #1e293b; padding: 32px; border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,.5); max-width: 560px; width: 100%; }
    h1 { margin: 0 0 4px; font-size: 24px; }
    .sub { color: #94a3b8; font-size: 14px; margin-bottom: 20px; }

    .stations { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
    .stations button {
        background: #0f172a; color: #cbd5e1; border: 1px solid #334155;
        padding: 8px 14px; border-radius: 999px; font-size: 13px;
        cursor: pointer; transition: all .15s;
    }
    .stations button:hover { border-color: #64748b; color: #fff; }
    .stations button.active {
        background: #10b981; border-color: #10b981; color: #052e1e; font-weight: 600;
    }
    .stations .empty { color: #64748b; font-size: 13px; }

    audio { width: 100%; }
    .hint { margin-top: 8px; font-size: 12px; color: #94a3b8; }

    .now { background: #0f172a; padding: 16px; border-radius: 12px; margin-top: 20px; }
    .label { color: #64748b; font-size: 12px; text-transform: uppercase;
              letter-spacing: .5px; margin-top: 12px; }
    .label:first-child { margin-top: 0; }
    .value { font-size: 16px; font-weight: 500; margin-top: 2px; }
    .meta { display: flex; gap: 16px; color: #94a3b8; font-size: 13px; margin-top: 12px;
            flex-wrap: wrap; }
    .badge { background: #10b981; color: #052e1e; padding: 2px 8px;
             border-radius: 99px; font-size: 11px; font-weight: 600; }
    .badge.live { background: #ef4444; color: #fff; }
</style>
</head>
<body>
    <div class="card">
        <h1 id="station-name">Quadrix Radio</h1>
        <div class="sub" id="station-desc">Multi-station live player</div>

        <div class="label">Stations</div>
        <div class="stations" id="stations"><span class="empty">Loading…</span></div>

        <audio id="player" controls autoplay preload="none"></audio>
        <div class="hint">⚡ Pause/Play bossangiz avtomatik live joyga sakraydi.</div>

        <div class="now">
            <div class="label">Now playing</div>
            <div class="value" id="title">—</div>
            <div class="meta">
                <span id="artist">—</span>
                <span id="elapsed">0s</span>
                <span id="duration">0s</span>
                <span id="badge"></span>
            </div>

            <div class="label">Up next</div>
            <div class="value" id="next">—</div>

            <div class="meta">
                <span>👥 <b id="listeners">0</b> listener(s)</span>
                <span>📡 <span id="online">offline</span></span>
                <span>⏱ updates every 4s</span>
            </div>
        </div>
    </div>
<script>
const player = document.getElementById('player');
const initialSlug = '__INITIAL_SLUG__';
let currentSlug = initialSlug || '';
let pausedByUser = false;
let pollTimer = null;

function streamUrl(slug, bust) {
    let u = '/api/radio/stream.mp3';
    if (slug) u += '?station=' + encodeURIComponent(slug);
    if (bust) u += (slug ? '&' : '?') + '_t=' + Date.now();
    return u;
}

function currentUrl(slug) {
    let u = '/api/radio/current/';
    if (slug) u += '?station=' + encodeURIComponent(slug);
    return u;
}

function loadStream(slug, autoplay) {
    pausedByUser = false;
    player.pause();
    player.src = streamUrl(slug, true);
    player.load();
    if (autoplay !== false) {
        const p = player.play();
        if (p) p.catch(() => {});
    }
}

function switchStation(slug, name) {
    if (slug === currentSlug) return;
    currentSlug = slug;
    document.querySelectorAll('.stations button').forEach(b => {
        b.classList.toggle('active', b.dataset.slug === slug);
    });
    document.getElementById('station-name').textContent = name || 'Quadrix Radio';
    history.replaceState(null, '', '?station=' + slug);
    loadStream(slug);
    poll();   // refresh metadata immediately
}

// HTML5 <audio> buferi ~10-30s oldinda. Pause qilib resume bosilganda eski audio
// chalmasligi uchun source URL'ni cache-buster bilan reload qilamiz → bufer
// tozalanadi, brauzer serverga yangi GET so'rov yuboradi → live joyga sakraydi.
player.addEventListener('pause', () => {
    if (!player.ended && player.readyState >= 2) pausedByUser = true;
});

player.addEventListener('play', () => {
    if (!pausedByUser) return;
    pausedByUser = false;
    player.src = streamUrl(currentSlug, true);
    player.load();
    const p = player.play();
    if (p) p.catch(() => {});
});

async function poll() {
    try {
        const r = await fetch(currentUrl(currentSlug));
        const d = await r.json();
        const ct = d.current_track || {};
        document.getElementById('title').textContent = ct.title || '—';
        document.getElementById('artist').textContent = ct.artist || '';
        document.getElementById('elapsed').textContent = (ct.elapsed || 0) + 's';
        document.getElementById('duration').textContent = (ct.duration || 0) + 's';
        document.getElementById('next').textContent = (d.next_track && d.next_track.title) || '—';
        document.getElementById('listeners').textContent = d.listeners || 0;
        document.getElementById('online').textContent = d.online ? 'online' : 'offline';
        const b = document.getElementById('badge');
        if (d.is_live) { b.textContent = 'LIVE'; b.className = 'badge live'; }
        else { b.textContent = 'AUTO'; b.className = 'badge'; }
    } catch (e) { console.error(e); }
}

async function loadStations() {
    const r = await fetch('/api/radio/stations/');
    const stations = await r.json();
    const container = document.getElementById('stations');
    container.innerHTML = '';
    if (!stations.length) {
        container.innerHTML = '<span class="empty">No stations configured.</span>';
        return;
    }

    if (!currentSlug) currentSlug = (stations.find(s => s.is_default) || stations[0]).slug;
    const active = stations.find(s => s.slug === currentSlug) || stations[0];
    document.getElementById('station-name').textContent = active.name;
    document.getElementById('station-desc').textContent = active.description || 'Multi-station live player';

    stations.forEach(s => {
        const btn = document.createElement('button');
        btn.textContent = s.name;
        btn.dataset.slug = s.slug;
        if (s.slug === currentSlug) btn.classList.add('active');
        btn.addEventListener('click', () => switchStation(s.slug, s.name));
        container.appendChild(btn);
    });

    loadStream(currentSlug);
    poll();
}

loadStations();
if (pollTimer) clearInterval(pollTimer);
pollTimer = setInterval(poll, 4000);
</script>
</body>
</html>"""


class StreamView(View):
    """GET /api/radio/stream.mp3?station=<slug>

    Continuous MP3 stream. The mobile app connects ONCE and listens forever
    while polling /api/radio/current/ separately for now-playing metadata.

    Async under ASGI (daphne) so that streaming truly streams instead of
    being wrapped in sync_to_async per chunk (which buffers).
    """

    async def get(self, request, *_, **__):
        import asyncio
        from asgiref.sync import sync_to_async

        slug = request.GET.get('station')
        station = await sync_to_async(_resolve_station, thread_sensitive=False)(slug)
        broadcaster = broadcaster_service.get_for_station(station.id)
        listener_q = broadcaster.subscribe()
        loop = asyncio.get_running_loop()

        async def stream():
            try:
                while True:
                    try:
                        chunk = await loop.run_in_executor(
                            None, _blocking_get, listener_q, 30,
                        )
                    except queue.Empty:
                        return
                    if chunk is None:
                        return
                    yield chunk
            finally:
                broadcaster.unsubscribe(listener_q)

        response = StreamingHttpResponse(stream(), content_type='audio/mpeg')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['icy-name'] = station.name
        response['icy-br'] = str(station.bitrate)
        response['icy-pub'] = '0'
        response['Accept-Ranges'] = 'none'
        return response


def _blocking_get(q, timeout):
    return q.get(timeout=timeout)
