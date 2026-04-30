"""DJ playlist editor API: CRUD playlists, items, reorder, now-state."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from radio.models import (
    AudioTrack, Playlist, PlaylistItem, PlaylistStatus, RadioStation, StationState,
)


# ----- helpers -----

def _resolve_station(slug: str) -> RadioStation:
    try:
        return RadioStation.objects.get(slug=slug, is_active=True)
    except RadioStation.DoesNotExist as exc:
        raise Http404('Station not found') from exc


def _serialize_playlist(pl: Playlist, *, with_items: bool = False, request=None) -> dict:
    data = {
        'id': pl.id,
        'title': pl.title,
        'description': pl.description,
        'date': pl.date,
        'station': {'id': pl.station_id, 'slug': pl.station.slug, 'name': pl.station.name},
        'status': pl.status,
        'is_fallback': pl.is_fallback,
        'auto_repeat': pl.auto_repeat,
        'shuffle': pl.shuffle,
        'total_duration': pl.total_duration,
        'item_count': pl.items.count(),
        'created_at': pl.created_at,
        'updated_at': pl.updated_at,
    }
    if with_items:
        data['items'] = [_serialize_item(it, request=request)
                         for it in pl.items.select_related('track').order_by('order', 'id')]
    return data


def _serialize_item(it: PlaylistItem, *, request=None) -> dict:
    audio_url = ''
    if it.track and it.track.audio_file:
        try:
            audio_url = it.track.audio_file.url
            if request is not None:
                audio_url = request.build_absolute_uri(audio_url)
        except Exception:
            pass
    return {
        'id': it.id,
        'order': it.order,
        'planned_start': it.planned_start,
        'planned_end': it.planned_end,
        'is_skipped': it.is_skipped,
        'note': it.note,
        'play_count': it.play_count,
        'last_played_at': it.last_played_at,
        'track': {
            'id': it.track_id,
            'title': it.track.title,
            'artist': it.track.artist,
            'duration_seconds': it.track.duration_seconds,
            'duration_display': it.track.duration_display,
            'category': it.track.category,
            'audio_url': audio_url,
        },
    }


def _renumber(playlist: Playlist) -> None:
    """Compact `order` values to 1..N to remove gaps after deletes."""
    items = list(playlist.items.order_by('order', 'id'))
    for i, it in enumerate(items, 1):
        if it.order != i:
            PlaylistItem.objects.filter(pk=it.id).update(order=i)


# ----- playlist views -----

class PlaylistListView(APIView):
    """GET/POST /api/radio/dj/playlists/"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        qs = Playlist.objects.select_related('station')

        slug = request.GET.get('station')
        if slug:
            qs = qs.filter(station__slug=slug)

        d_from = request.GET.get('date_from')
        d_to = request.GET.get('date_to')
        if d_from:
            qs = qs.filter(date__gte=d_from)
        if d_to:
            qs = qs.filter(date__lte=d_to)

        only_status = request.GET.get('status')
        if only_status:
            qs = qs.filter(status=only_status)

        return Response([_serialize_playlist(p) for p in qs.order_by('-date', '-id')[:200]])

    def post(self, request):
        slug = request.data.get('station')
        date_str = request.data.get('date')
        if not slug or not date_str:
            return Response({'detail': 'station and date are required'},
                            status=status.HTTP_400_BAD_REQUEST)
        station = _resolve_station(slug)
        try:
            d = datetime.fromisoformat(date_str).date()
        except ValueError:
            return Response({'detail': 'date must be ISO format (YYYY-MM-DD)'},
                            status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title') or f'{station.name} — {d.isoformat()}'
        playlist, created = Playlist.objects.get_or_create(
            station=station, date=d, region=None, segment=None,
            defaults={
                'title': title,
                'description': request.data.get('description', ''),
                'status': request.data.get('status') or PlaylistStatus.SCHEDULED,
                'is_fallback': bool(request.data.get('is_fallback', False)),
                'auto_repeat': bool(request.data.get('auto_repeat', True)),
                'shuffle': bool(request.data.get('shuffle', False)),
            },
        )
        return Response(
            _serialize_playlist(playlist, with_items=True, request=request),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PlaylistDetailView(APIView):
    """GET/PATCH/DELETE /api/radio/dj/playlists/<id>/"""
    permission_classes = (IsAuthenticated,)

    def _obj(self, pk):
        try:
            return Playlist.objects.select_related('station').get(pk=pk)
        except Playlist.DoesNotExist as exc:
            raise Http404 from exc

    def get(self, request, pk):
        return Response(_serialize_playlist(self._obj(pk), with_items=True, request=request))

    def patch(self, request, pk):
        pl = self._obj(pk)
        editable = (
            'title', 'description', 'status', 'is_fallback',
            'auto_repeat', 'shuffle', 'date',
        )
        for field in editable:
            if field in request.data:
                value = request.data[field]
                if field == 'date' and isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value).date()
                    except ValueError:
                        return Response({'detail': 'invalid date'},
                                        status=status.HTTP_400_BAD_REQUEST)
                setattr(pl, field, value)
        pl.save()
        return Response(_serialize_playlist(pl, with_items=True, request=request))

    def delete(self, request, pk):
        self._obj(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ----- item views -----

class PlaylistItemAddView(APIView):
    """POST /api/radio/dj/playlists/<id>/items/   body: {track_id, order?, planned_start?, note?}"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, playlist_id):
        try:
            playlist = Playlist.objects.get(pk=playlist_id)
        except Playlist.DoesNotExist as exc:
            raise Http404 from exc

        track_id = request.data.get('track_id')
        if not track_id:
            return Response({'detail': 'track_id is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            track = AudioTrack.objects.get(pk=track_id)
        except AudioTrack.DoesNotExist:
            return Response({'detail': 'track not found'},
                            status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            requested_order = request.data.get('order')
            if requested_order is None:
                # Append at the end
                last = playlist.items.aggregate(m=models_max_order())
                next_order = (last['m'] or 0) + 1
            else:
                try:
                    next_order = int(requested_order)
                except (TypeError, ValueError):
                    return Response({'detail': 'order must be integer'},
                                    status=status.HTTP_400_BAD_REQUEST)
                # Bump everyone at or after this order
                playlist.items.filter(order__gte=next_order).update(order=F('order') + 1)

            item = PlaylistItem.objects.create(
                playlist=playlist,
                track=track,
                order=next_order,
                planned_start=request.data.get('planned_start') or None,
                planned_end=request.data.get('planned_end') or None,
                note=request.data.get('note', ''),
            )

        return Response(_serialize_item(item, request=request), status=status.HTTP_201_CREATED)


class PlaylistItemDetailView(APIView):
    """PATCH/DELETE /api/radio/dj/playlist-items/<id>/"""
    permission_classes = (IsAuthenticated,)

    def _obj(self, pk):
        try:
            return PlaylistItem.objects.select_related('track', 'playlist').get(pk=pk)
        except PlaylistItem.DoesNotExist as exc:
            raise Http404 from exc

    def patch(self, request, pk):
        item = self._obj(pk)
        for field in ('planned_start', 'planned_end', 'is_skipped', 'note'):
            if field in request.data:
                value = request.data[field]
                if field.startswith('planned_') and not value:
                    value = None
                setattr(item, field, value)
        # Order changes have to renumber siblings; handle separately.
        if 'order' in request.data:
            try:
                new_order = int(request.data['order'])
            except (TypeError, ValueError):
                return Response({'detail': 'order must be integer'},
                                status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                old_order = item.order
                if new_order != old_order:
                    if new_order < old_order:
                        # shift up
                        item.playlist.items.filter(
                            order__gte=new_order, order__lt=old_order,
                        ).exclude(pk=item.pk).update(order=F('order') + 1)
                    else:
                        item.playlist.items.filter(
                            order__lte=new_order, order__gt=old_order,
                        ).exclude(pk=item.pk).update(order=F('order') - 1)
                    item.order = new_order
                item.save()
                _renumber(item.playlist)
        else:
            item.save()
        item.refresh_from_db()
        return Response(_serialize_item(item, request=request))

    def delete(self, request, pk):
        item = self._obj(pk)
        playlist = item.playlist
        item.delete()
        _renumber(playlist)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlaylistReorderView(APIView):
    """POST /api/radio/dj/playlists/<id>/reorder/   body: {item_ids: [3, 1, 4, 2]}"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, playlist_id):
        try:
            playlist = Playlist.objects.get(pk=playlist_id)
        except Playlist.DoesNotExist as exc:
            raise Http404 from exc

        ids = request.data.get('item_ids')
        if not isinstance(ids, list):
            return Response({'detail': 'item_ids must be a list'},
                            status=status.HTTP_400_BAD_REQUEST)

        valid_ids = set(playlist.items.values_list('id', flat=True))
        if set(ids) != valid_ids:
            return Response(
                {'detail': 'item_ids must include exactly all playlist item IDs'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            for i, item_id in enumerate(ids, 1):
                PlaylistItem.objects.filter(pk=item_id).update(order=i)

        return Response(_serialize_playlist(playlist, with_items=True, request=request))


# ----- now-playing state -----

class NowStateView(APIView):
    """GET /api/radio/dj/now/?station=<slug>

    Returns full broadcast state for the DJ dashboard:
        { is_live, current, history (played items), upcoming (queued items),
          listeners, online }
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        slug = request.GET.get('station')
        if not slug:
            return Response({'detail': 'station is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        station = _resolve_station(slug)

        from radio.services import playlist as playlist_service
        playlist = playlist_service.select_playlist(station)
        state = StationState.objects.filter(station=station).first()

        current = None
        history = []
        upcoming = []
        items = []

        if playlist is not None:
            items = list(
                playlist.items.select_related('track').order_by('order', 'id')
            )

        current_item_id = state.current_item_id if state else None
        current_track_id = state.current_track_id if state else None

        # Find the current item by ID match; if absent, use track ID; if still
        # absent, leave current=None.
        current_idx = -1
        if current_item_id:
            for i, it in enumerate(items):
                if it.id == current_item_id:
                    current_idx = i
                    break
        if current_idx == -1 and current_track_id:
            for i, it in enumerate(items):
                if it.track_id == current_track_id:
                    current_idx = i
                    break

        if current_idx >= 0:
            it = items[current_idx]
            elapsed = 0
            if state and state.current_started_at:
                elapsed = max(0, int((timezone.now() - state.current_started_at).total_seconds()))
            current = {
                **_serialize_item(it, request=request),
                'started_at': state.current_started_at if state else None,
                'ends_at': state.current_ends_at if state else None,
                'elapsed_seconds': elapsed,
                'remaining_seconds': max(0, (it.track.duration_seconds or 0) - elapsed),
            }

            for it in items[:current_idx]:
                history.append(_serialize_item(it, request=request))
            for it in items[current_idx + 1:]:
                upcoming.append(_serialize_item(it, request=request))
        else:
            upcoming = [_serialize_item(it, request=request) for it in items]

        return Response({
            'station': {'id': station.id, 'slug': station.slug, 'name': station.name},
            'is_live': bool(state and state.is_live),
            'live_broadcast_id': state.live_broadcast_id if state else None,
            'online': bool(state and state.online),
            'listeners': state.listeners if state else 0,
            'playlist': _serialize_playlist(playlist) if playlist else None,
            'current': current,
            'history': history,
            'upcoming': upcoming,
        })


# Helpers ------------------------------------------------------------------

def models_max_order():
    """`Max('order')` factory that doesn't pollute imports up top."""
    from django.db.models import Max
    return Max('order')
