from django.urls import path

from radio.api.dj_dashboard import DJDashboardView
from radio.api.dj_library import TrackDetailView, TrackLibraryView
from radio.api.dj_playlists import (
    NowStateView, PlaylistDetailView, PlaylistItemAddView,
    PlaylistItemDetailView, PlaylistListView, PlaylistReorderView,
)
from radio.api.dj_views import (
    DJDashboardInfoView, DJLiveStartView, DJLiveStatusView, DJLiveStopView,
    DJLiveUploadView, DJQueuePushView, DJSkipView,
)
from radio.api.views import (
    CurrentView, LiveCurrentView, StationDetailView, StationListView,
    StatusView, StreamView, TestPlayerView, TodayPlaylistView,
)

app_name = 'radio'

urlpatterns = [
    # ----- Public listener API -----
    path('stations/', StationListView.as_view(), name='station-list'),
    path('stations/<slug:slug>/', StationDetailView.as_view(), name='station-detail'),
    path('current/', CurrentView.as_view(), name='current'),
    path('status/', StatusView.as_view(), name='status'),
    path('playlist/today/', TodayPlaylistView.as_view(), name='playlist-today'),
    path('live/', LiveCurrentView.as_view(), name='live-current'),
    path('stream.mp3', StreamView.as_view(), name='stream'),
    path('stream', StreamView.as_view()),
    path('test/', TestPlayerView.as_view(), name='test-player'),

    # ----- DJ dashboard -----
    path('dj/', DJDashboardView.as_view(), name='dj-dashboard'),
    path('dj/me/', DJDashboardInfoView.as_view(), name='dj-me'),
    path('dj/live/start/', DJLiveStartView.as_view(), name='dj-live-start'),
    path('dj/live/<int:broadcast_id>/upload/',
         DJLiveUploadView.as_view(), name='dj-live-upload'),
    path('dj/live/<int:broadcast_id>/stop/',
         DJLiveStopView.as_view(), name='dj-live-stop'),
    path('dj/live/<int:broadcast_id>/status/',
         DJLiveStatusView.as_view(), name='dj-live-status'),
    path('dj/skip/', DJSkipView.as_view(), name='dj-skip'),
    path('dj/queue/push/', DJQueuePushView.as_view(), name='dj-queue-push'),

    # ----- DJ track library + playlist editor -----
    path('dj/library/', TrackLibraryView.as_view(), name='dj-library'),
    path('dj/library/<int:pk>/', TrackDetailView.as_view(), name='dj-library-detail'),

    path('dj/now/', NowStateView.as_view(), name='dj-now'),

    path('dj/playlists/', PlaylistListView.as_view(), name='dj-playlists'),
    path('dj/playlists/<int:pk>/', PlaylistDetailView.as_view(), name='dj-playlist-detail'),
    path('dj/playlists/<int:playlist_id>/items/',
         PlaylistItemAddView.as_view(), name='dj-playlist-items-add'),
    path('dj/playlists/<int:playlist_id>/reorder/',
         PlaylistReorderView.as_view(), name='dj-playlist-reorder'),
    path('dj/playlist-items/<int:pk>/',
         PlaylistItemDetailView.as_view(), name='dj-playlist-item-detail'),
]
