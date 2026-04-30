from django.urls import path

from ads.api.views import AdLogView, AdNextView

app_name = 'ads'

urlpatterns = [
    path('next/', AdNextView.as_view(), name='ad-next'),
    path('log/', AdLogView.as_view(), name='ad-log'),
]
