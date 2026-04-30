"""DJ-facing endpoints: live mic, skip, queue control, dashboard."""

from __future__ import annotations

import logging

from django.db.models import F
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from radio.models import (
    AudioTrack, LiveBroadcast, LiveStatus, PlaylistItem, RadioStation, StationState,
)
from radio.services import broadcaster as broadcaster_service
from radio.services import live_session as live_session_service

logger = logging.getLogger(__name__)


# Anything mutating that uses session auth needs CSRF; uploads use stream_key.
def _resolve_station(slug: str) -> RadioStation:
    try:
        return RadioStation.objects.get(slug=slug, is_active=True)
    except RadioStation.DoesNotExist as exc:
        raise Http404('Station not found') from exc


class DJDashboardInfoView(APIView):
    """GET /api/radio/dj/me/  — info about the logged-in DJ + active broadcasts."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        active = LiveBroadcast.objects.filter(
            started_by=request.user, status=LiveStatus.LIVE,
        ).values('id', 'station__slug', 'station__name', 'title',
                 'started_at', 'stream_key', 'mount_point')
        return Response({
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'is_staff': request.user.is_staff,
            },
            'active_broadcasts': list(active),
            'stations': list(
                RadioStation.objects.filter(is_active=True)
                .values('id', 'slug', 'name', 'is_live', 'listeners_cached')
            ),
        })


class DJLiveStartView(APIView):
    """POST /api/radio/dj/live/start/

    Body: {"station": "<slug>", "title": "On-air name", "description": "..."}
    Returns: {broadcast_id, stream_key, station, upload_url, stop_url}
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        slug = request.data.get('station')
        if not slug:
            return Response({'detail': 'station is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        station = _resolve_station(slug)

        # End any of this DJ's previously-live broadcasts on the same station —
        # avoids zombies if the browser tab was closed without clicking Stop.
        for old in LiveBroadcast.objects.filter(
            station=station, status=LiveStatus.LIVE,
        ):
            self._end_broadcast(old)

        live = LiveBroadcast.objects.create(
            station=station,
            title=request.data.get('title') or 'Live broadcast',
            description=request.data.get('description', ''),
            status=LiveStatus.LIVE,
            started_at=timezone.now(),
            started_by=request.user,
        )
        RadioStation.objects.filter(pk=station.pk).update(is_live=True)

        return Response({
            'broadcast_id': live.id,
            'stream_key': live.stream_key,
            'station': station.slug,
            'started_at': live.started_at,
            'upload_url': f'/api/radio/dj/live/{live.id}/upload/',
            'stop_url': f'/api/radio/dj/live/{live.id}/stop/',
            'status_url': f'/api/radio/dj/live/{live.id}/status/',
            'listener_stream_url': f'/api/radio/stream.mp3?station={station.slug}',
        }, status=status.HTTP_201_CREATED)

    @staticmethod
    def _end_broadcast(live: LiveBroadcast):
        live.status = LiveStatus.ENDED
        live.ended_at = timezone.now()
        live.save(update_fields=['status', 'ended_at', 'updated_at'])
        sess = live_session_service.remove(live.id)
        broadcaster = broadcaster_service.get_for_station(live.station_id)
        broadcaster.detach_live()
        if sess is not None:
            sess.stop()
        RadioStation.objects.filter(pk=live.station_id).update(is_live=False)


@method_decorator(csrf_exempt, name='dispatch')
class DJLiveUploadView(View):
    """POST /api/radio/dj/live/<id>/upload/

    Headers:
        X-Stream-Key:    <stream_key returned by /start/>
        X-Audio-Format:  webm | mp4 | ogg   (default: webm)
        Content-Type:    audio/webm  (informational)

    Body: raw bytes from MediaRecorder.ondataavailable.
    """

    def post(self, request, broadcast_id: int):
        key = (
            request.headers.get('X-Stream-Key')
            or request.GET.get('key')
            or ''
        )
        if not key:
            return HttpResponse('missing stream key', status=401)

        try:
            live = LiveBroadcast.objects.select_related('station').get(
                pk=broadcast_id, stream_key=key,
            )
        except LiveBroadcast.DoesNotExist:
            return HttpResponse('invalid stream key', status=403)

        if live.status != LiveStatus.LIVE:
            return HttpResponse('broadcast not live', status=409)

        chunk = request.body
        if not chunk:
            return HttpResponse('', status=204)

        input_format = request.headers.get('X-Audio-Format', 'webm').lower()
        if input_format not in {'webm', 'mp4', 'ogg', 'mpegts'}:
            input_format = 'webm'

        sess = live_session_service.get(broadcast_id)
        if sess is None:
            sess = live_session_service.get_or_create(
                broadcast_id, input_format=input_format,
            )
            if sess is None:
                return HttpResponse('ffmpeg unavailable', status=503)
            broadcaster = broadcaster_service.get_for_station(live.station_id)
            broadcaster.attach_live(sess)

        ok = sess.feed(chunk)
        if not ok:
            return HttpResponse('feed failed (ffmpeg dead?)', status=502)
        return HttpResponse('', status=204)


class DJLiveStopView(APIView):
    """POST /api/radio/dj/live/<id>/stop/  — end the live broadcast."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, broadcast_id):
        try:
            live = LiveBroadcast.objects.get(pk=broadcast_id)
        except LiveBroadcast.DoesNotExist:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        if live.started_by_id and live.started_by_id != request.user.id and not request.user.is_staff:
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

        DJLiveStartView._end_broadcast(live)

        duration = 0
        if live.started_at and live.ended_at:
            duration = int((live.ended_at - live.started_at).total_seconds())

        return Response({
            'ok': True,
            'broadcast_id': live.id,
            'duration_seconds': duration,
        })


class DJLiveStatusView(APIView):
    """GET /api/radio/dj/live/<id>/status/  — listeners, bytes in/out, alive flag."""
    permission_classes = (IsAuthenticated,)

    def get(self, request, broadcast_id):
        try:
            live = LiveBroadcast.objects.select_related('station').get(pk=broadcast_id)
        except LiveBroadcast.DoesNotExist:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        sess = live_session_service.get(broadcast_id)
        broadcaster = broadcaster_service.get_for_station(live.station_id)
        listeners = broadcaster.listener_count

        return Response({
            'broadcast_id': live.id,
            'station': live.station.slug,
            'title': live.title,
            'status': live.status,
            'started_at': live.started_at,
            'ended_at': live.ended_at,
            'is_live_session_alive': bool(sess and sess.is_alive()),
            'is_session_stale': bool(sess and sess.is_stale()),
            'bytes_in': sess.bytes_in if sess else 0,
            'bytes_out': sess.bytes_out if sess else 0,
            'listeners': listeners,
        })


class DJSkipView(APIView):
    """POST /api/radio/dj/skip/   body: {"station": "<slug>"}

    Force the broadcaster to advance to the next track immediately. Has no
    effect during live mic mode.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        slug = request.data.get('station')
        if not slug:
            return Response({'detail': 'station is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        station = _resolve_station(slug)

        # Tell the in-process broadcaster to abandon the current track. The
        # state-update is also kept so any cold producer that hasn't started
        # yet picks the right track on first tick.
        broadcaster = broadcaster_service.get_for_station(station.id)
        broadcaster.skip()
        StationState.objects.filter(station=station).update(
            current_ends_at=timezone.now(),
        )
        return Response({'ok': True})


class DJQueuePushView(APIView):
    """POST /api/radio/dj/queue/push/   body: {"station": "<slug>", "track_id": 5}

    Insert a track right after the currently-playing one in today's playlist.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        slug = request.data.get('station')
        track_id = request.data.get('track_id')
        if not slug or not track_id:
            return Response({'detail': 'station and track_id are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        station = _resolve_station(slug)
        try:
            track = AudioTrack.objects.get(pk=track_id)
        except AudioTrack.DoesNotExist:
            return Response({'detail': 'track not found'},
                            status=status.HTTP_404_NOT_FOUND)

        from radio.services import playlist as playlist_service
        playlist = playlist_service.select_playlist(station)
        if playlist is None:
            return Response({'detail': 'no active playlist'},
                            status=status.HTTP_404_NOT_FOUND)

        state = StationState.objects.filter(station=station).first()
        current_order = 0
        if state and state.current_item_id:
            current_item = PlaylistItem.objects.filter(pk=state.current_item_id).first()
            if current_item:
                current_order = current_item.order

        # Bump everyone after current_order by 1, then insert at current_order+1.
        PlaylistItem.objects.filter(
            playlist=playlist, order__gt=current_order,
        ).update(order=F('order') + 1)
        new_item = PlaylistItem.objects.create(
            playlist=playlist, track=track, order=current_order + 1,
            note=f'Queued by {request.user.username}',
        )
        return Response({
            'ok': True, 'playlist_item_id': new_item.id,
            'position_after': current_order,
        }, status=status.HTTP_201_CREATED)


