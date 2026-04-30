from django.urls import path

from notifications.api.views import DeviceRegisterView, DeviceUnregisterView

app_name = 'notifications'

urlpatterns = [
    path('devices/register/', DeviceRegisterView.as_view(), name='device-register'),
    path('devices/unregister/', DeviceUnregisterView.as_view(), name='device-unregister'),
]
