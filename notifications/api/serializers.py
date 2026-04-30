from rest_framework import serializers

from notifications.models import Device, Platform


class DeviceRegisterSerializer(serializers.Serializer):
    push_token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=Platform.choices)
    device_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True)
    locale = serializers.CharField(max_length=16, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    region_id = serializers.IntegerField(required=False, allow_null=True)
    segment_id = serializers.IntegerField(required=False, allow_null=True)


class DeviceUnregisterSerializer(serializers.Serializer):
    push_token = serializers.CharField(max_length=512)


class DevicePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = (
            'id', 'platform', 'device_id', 'app_version',
            'locale', 'timezone', 'is_active',
            'region', 'segment',
        )
