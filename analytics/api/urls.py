from django.urls import path

from analytics.api.views import (
    DailyStatsView, SessionEndView, SessionEventView,
    SessionHeartbeatView, SessionStartView,
)

app_name = 'analytics'

urlpatterns = [
    path('session/start/', SessionStartView.as_view(), name='session-start'),
    path('session/heartbeat/', SessionHeartbeatView.as_view(), name='session-heartbeat'),
    path('session/end/', SessionEndView.as_view(), name='session-end'),
    path('event/', SessionEventView.as_view(), name='event'),
    path('stats/daily/', DailyStatsView.as_view(), name='stats-daily'),
]
