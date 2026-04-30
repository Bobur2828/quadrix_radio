"""Listener session tracking & stats APIs."""

from __future__ import annotations

from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from analytics.api.serializers import (
    DailyStatsSerializer, EventSerializer, HeartbeatSerializer,
    SessionPublicSerializer, SessionStartSerializer,
)
from analytics.models import (
    DailyStats, DriverSegment, ListenerEvent, ListenerSession, Region,
)
from analytics.services import geo as geo_service
from radio.models import RadioStation


def _client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


class SessionStartView(APIView):
    """POST /api/analytics/session/start/

    Mobile app starts a listening session. Returns a session UUID and the
    heartbeat interval the app should respect.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = SessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            station = RadioStation.objects.get(slug=d['station'], is_active=True)
        except RadioStation.DoesNotExist as exc:
            raise Http404('Station not found') from exc

        ip = _client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')[:255]

        region_id = d.get('region_id')
        country = ''
        state_code = ''
        if region_id is None:
            geo = geo_service.resolve(ip)
            country = geo.country
            state_code = geo.state_code
            region_id = geo.region.id if geo.region else None
        else:
            if not Region.objects.filter(pk=region_id).exists():
                region_id = None

        segment_id = d.get('segment_id')
        if segment_id and not DriverSegment.objects.filter(pk=segment_id).exists():
            segment_id = None

        session = ListenerSession.objects.create(
            station=station,
            user=request.user if request.user.is_authenticated else None,
            device_id=d.get('device_id', '') or '',
            platform=d.get('platform', '') or '',
            app_version=d.get('app_version', '') or '',
            ip_address=ip or None,
            user_agent=ua,
            country=country,
            state_code=state_code,
            region_id=region_id,
            segment_id=segment_id,
        )
        ListenerEvent.objects.create(
            session=session, event_type=ListenerEvent.EventType.START,
        )

        data = SessionPublicSerializer(session).data
        return Response(data, status=status.HTTP_201_CREATED)


class SessionHeartbeatView(APIView):
    """POST /api/analytics/session/heartbeat/

    Mobile app pings every ~30 s. We update last_heartbeat_at; if absent
    too long, expire_stale_sessions() ends them.
    """
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'session_heartbeat'

    def post(self, request):
        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = ListenerSession.objects.get(
                public_id=serializer.validated_data['session_id'],
                ended_at__isnull=True,
            )
        except ListenerSession.DoesNotExist as exc:
            raise Http404('Session not found') from exc

        session.touch()
        return Response({'ok': True, 'received_at': timezone.now()})


class SessionEndView(APIView):
    """POST /api/analytics/session/end/"""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = ListenerSession.objects.get(
                public_id=serializer.validated_data['session_id'],
            )
        except ListenerSession.DoesNotExist as exc:
            raise Http404('Session not found') from exc

        if session.ended_at is None:
            session.end()
            ListenerEvent.objects.create(
                session=session, event_type=ListenerEvent.EventType.END,
            )
        return Response({'ok': True, 'duration_seconds': session.duration_seconds})


class SessionEventView(APIView):
    """POST /api/analytics/event/  — log a track_play / ad_play / error"""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            session = ListenerSession.objects.get(public_id=d['session_id'])
        except ListenerSession.DoesNotExist as exc:
            raise Http404('Session not found') from exc

        ListenerEvent.objects.create(
            session=session,
            event_type=d['event_type'],
            track_id=d.get('track_id'),
            payload=d.get('payload') or {},
        )
        return Response({'ok': True}, status=status.HTTP_201_CREATED)


class DailyStatsView(APIView):
    """GET /api/analytics/stats/daily/?station=<slug>&from=<date>&to=<date>"""
    permission_classes = (AllowAny,)

    def get(self, request):
        slug = request.query_params.get('station')
        if not slug:
            return Response({'detail': 'station is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            station = RadioStation.objects.get(slug=slug)
        except RadioStation.DoesNotExist as exc:
            raise Http404('Station not found') from exc

        qs = DailyStats.objects.filter(station=station)
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return Response(DailyStatsSerializer(qs[:90], many=True).data)
