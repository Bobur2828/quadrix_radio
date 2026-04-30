from django.http import Http404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ads.api.serializers import (
    AdLogSerializer, AdNextRequestSerializer, AdPublicSerializer,
)
from ads.models import SponsoredAd
from ads.services import scheduler as ad_scheduler
from analytics.models import ListenerSession
from radio.models import RadioStation


class AdNextView(APIView):
    """POST /api/ads/next/  — pick the next ad for a listener."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = AdNextRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            station = RadioStation.objects.get(slug=d['station'], is_active=True)
        except RadioStation.DoesNotExist as exc:
            raise Http404('Station not found') from exc

        ad = ad_scheduler.pick_next_ad(
            station,
            region_id=d.get('region_id'),
            segment_id=d.get('segment_id'),
        )
        if ad is None:
            return Response({'ad': None})

        url = ad.audio_file.url
        url = request.build_absolute_uri(url)
        return Response({
            'ad': AdPublicSerializer({
                'id': ad.id,
                'title': ad.title,
                'sponsor': ad.sponsor,
                'duration': ad.duration_seconds,
                'audio_url': url,
            }).data,
        }, status=status.HTTP_200_OK)


class AdLogView(APIView):
    """POST /api/ads/log/  — record an ad play (mobile-side fallback)."""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = AdLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            ad = SponsoredAd.objects.get(pk=d['ad_id'])
        except SponsoredAd.DoesNotExist as exc:
            raise Http404('Ad not found') from exc

        try:
            station = RadioStation.objects.get(slug=d['station'], is_active=True)
        except RadioStation.DoesNotExist as exc:
            raise Http404('Station not found') from exc

        session_pk = None
        if d.get('session_id'):
            session = (
                ListenerSession.objects.filter(public_id=d['session_id']).only('id', 'region_id').first()
            )
            session_pk = session.id if session else None
            region_id = session.region_id if session else None
        else:
            region_id = None

        ad_scheduler.log_ad_play(
            ad=ad, station=station,
            session_id=session_pk,
            region_id=region_id,
            completed=d.get('completed') or False,
            duration_seconds=d.get('duration_seconds') or 0,
        )
        return Response({'ok': True}, status=status.HTTP_201_CREATED)
