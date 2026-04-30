from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import DriverSegment, Region
from notifications.api.serializers import (
    DevicePublicSerializer, DeviceRegisterSerializer, DeviceUnregisterSerializer,
)
from notifications.models import Device


class DeviceRegisterView(APIView):
    """POST /api/notifications/devices/register/

    Idempotent — sends the same push_token twice updates the row.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = DeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        defaults = {
            'platform': d['platform'],
            'device_id': d.get('device_id', '') or '',
            'app_version': d.get('app_version', '') or '',
            'locale': d.get('locale', '') or '',
            'timezone': d.get('timezone', '') or '',
            'is_active': True,
            'failure_count': 0,
        }

        region_id = d.get('region_id')
        if region_id and Region.objects.filter(pk=region_id).exists():
            defaults['region_id'] = region_id

        segment_id = d.get('segment_id')
        if segment_id and DriverSegment.objects.filter(pk=segment_id).exists():
            defaults['segment_id'] = segment_id

        if request.user.is_authenticated:
            defaults['user'] = request.user

        device, _created = Device.objects.update_or_create(
            push_token=d['push_token'], defaults=defaults,
        )
        return Response(
            DevicePublicSerializer(device).data,
            status=status.HTTP_201_CREATED,
        )


class DeviceUnregisterView(APIView):
    """POST /api/notifications/devices/unregister/"""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = DeviceUnregisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        Device.objects.filter(push_token=serializer.validated_data['push_token']).update(
            is_active=False,
        )
        return Response({'ok': True})
