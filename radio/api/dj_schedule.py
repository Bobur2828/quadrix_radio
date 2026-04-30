"""DJ schedule API: shows, weekly schedule, recent episodes."""

from __future__ import annotations

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from radio.models import (
    AudioTrack, Playlist, PlaylistItem, PlaylistStatus, RadioStation,
    Show, ShowEpisode, ShowSchedule, WeekDay,
)
from radio.services import scheduler as scheduler_service


def _resolve_station(slug: str) -> RadioStation:
    try:
        return RadioStation.objects.get(slug=slug, is_active=True)
    except RadioStation.DoesNotExist as exc:
        raise Http404('Station not found') from exc


def _serialize_show(s: Show) -> dict:
    return {
        'id': s.id, 'slug': s.slug, 'name': s.name,
        'description': s.description, 'color': s.color,
        'station_id': s.station_id, 'station_slug': s.station.slug,
        'host_id': s.host_id,
        'host_name': s.host.username if s.host_id else None,
        'playlist_id': s.playlist_id,
        'playlist_title': s.playlist.title if s.playlist_id else None,
        'is_active': s.is_active,
    }


def _fmt_time(t) -> str:
    if t is None:
        return ''
    if hasattr(t, 'strftime'):
        return t.strftime('%H:%M')
    return str(t)[:5]


def _parse_time(value):
    """Parse 'HH:MM' or 'HH:MM:SS' into a datetime.time, or raise ValueError."""
    if value in (None, ''):
        return None
    if hasattr(value, 'hour'):
        return value
    from datetime import time as time_cls
    parts = str(value).split(':')
    if len(parts) < 2:
        raise ValueError('time must be HH:MM')
    return time_cls(int(parts[0]), int(parts[1]),
                    int(parts[2]) if len(parts) > 2 else 0)


def _serialize_schedule(sc: ShowSchedule) -> dict:
    return {
        'id': sc.id,
        'show_id': sc.show_id,
        'show_name': sc.show.name,
        'show_color': sc.show.color,
        'day_of_week': sc.day_of_week,
        'day_label': sc.get_day_of_week_display(),
        'start_time': _fmt_time(sc.start_time),
        'end_time': _fmt_time(sc.end_time),
        'is_active': sc.is_active,
        'note': sc.note,
        'crosses_midnight': sc.crosses_midnight,
    }


# ───────── Shows ─────────

class ShowListView(APIView):
    """GET/POST /api/radio/dj/shows/"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        qs = Show.objects.select_related('station', 'host', 'playlist')
        slug = request.GET.get('station')
        if slug:
            qs = qs.filter(station__slug=slug)
        return Response([_serialize_show(s) for s in qs.order_by('station', 'name')])

    def post(self, request):
        slug = request.data.get('station')
        name = request.data.get('name')
        if not slug or not name:
            return Response({'detail': 'station and name are required'},
                            status=status.HTTP_400_BAD_REQUEST)
        station = _resolve_station(slug)

        from django.utils.text import slugify
        base_slug = slugify(name)[:120] or 'show'
        candidate = base_slug
        i = 2
        while Show.objects.filter(slug=candidate).exists():
            candidate = f'{base_slug}-{i}'
            i += 1

        playlist_id = request.data.get('playlist_id')
        if playlist_id and not Playlist.objects.filter(pk=playlist_id).exists():
            playlist_id = None

        show = Show.objects.create(
            name=name,
            slug=candidate,
            description=request.data.get('description', ''),
            color=request.data.get('color', '#10b981'),
            station=station,
            host=request.user if request.data.get('host_self') else None,
            playlist_id=playlist_id,
        )
        return Response(_serialize_show(show), status=status.HTTP_201_CREATED)


class ShowDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _obj(self, pk):
        try:
            return Show.objects.select_related('station', 'host', 'playlist').get(pk=pk)
        except Show.DoesNotExist as exc:
            raise Http404 from exc

    def get(self, request, pk):
        show = self._obj(pk)
        data = _serialize_show(show)
        data['schedules'] = [_serialize_schedule(s) for s in show.schedules.all()]
        return Response(data)

    def patch(self, request, pk):
        show = self._obj(pk)
        for field in ('name', 'description', 'color', 'is_active'):
            if field in request.data:
                setattr(show, field, request.data[field])
        if 'playlist_id' in request.data:
            pid = request.data['playlist_id']
            show.playlist_id = pid if pid and Playlist.objects.filter(pk=pid).exists() else None
        if 'host_id' in request.data:
            from django.contrib.auth import get_user_model
            U = get_user_model()
            uid = request.data['host_id']
            show.host_id = uid if uid and U.objects.filter(pk=uid).exists() else None
        show.save()
        return Response(_serialize_show(show))

    def delete(self, request, pk):
        self._obj(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────── Schedules ─────────

class ScheduleListView(APIView):
    """GET /api/radio/dj/schedules/?station=<slug>
    POST /api/radio/dj/schedules/  body: {show_id, day_of_week, start_time, end_time}"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        qs = ShowSchedule.objects.select_related('show', 'show__station')
        slug = request.GET.get('station')
        if slug:
            qs = qs.filter(show__station__slug=slug)
        return Response([
            _serialize_schedule(s)
            for s in qs.order_by('day_of_week', 'start_time')
        ])

    def post(self, request):
        show_id = request.data.get('show_id')
        day = request.data.get('day_of_week')
        start = request.data.get('start_time')
        end = request.data.get('end_time')
        if not all([show_id, day is not None, start, end]):
            return Response(
                {'detail': 'show_id, day_of_week, start_time and end_time required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            show = Show.objects.get(pk=show_id)
        except Show.DoesNotExist:
            return Response({'detail': 'show not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            day = int(day)
        except (TypeError, ValueError):
            return Response({'detail': 'day_of_week must be 0..6'},
                            status=status.HTTP_400_BAD_REQUEST)
        if day not in WeekDay.values:
            return Response({'detail': 'day_of_week must be 0..6'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            start_t = _parse_time(start)
            end_t = _parse_time(end)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        schedule = ShowSchedule.objects.create(
            show=show, day_of_week=day,
            start_time=start_t, end_time=end_t,
            note=request.data.get('note', ''),
        )
        return Response(_serialize_schedule(schedule), status=status.HTTP_201_CREATED)


class ScheduleDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _obj(self, pk):
        try:
            return ShowSchedule.objects.select_related('show').get(pk=pk)
        except ShowSchedule.DoesNotExist as exc:
            raise Http404 from exc

    def patch(self, request, pk):
        sc = self._obj(pk)
        for field in ('day_of_week', 'is_active', 'note'):
            if field in request.data:
                setattr(sc, field, request.data[field])
        for field in ('start_time', 'end_time'):
            if field in request.data:
                try:
                    setattr(sc, field, _parse_time(request.data[field]))
                except ValueError as exc:
                    return Response({'detail': f'{field}: {exc}'},
                                    status=status.HTTP_400_BAD_REQUEST)
        sc.save()
        return Response(_serialize_schedule(sc))

    def delete(self, request, pk):
        self._obj(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────── One-shot wizard ─────────

class ShowWizardView(APIView):
    """POST /api/radio/dj/shows/wizard/

    Creates the show, its auto-DJ playlist (with the supplied tracks), and
    optionally a weekly schedule — all in one atomic transaction.

    Body:
        station:      slug
        name:         show name
        color:        hex (e.g. #f59e0b)
        track_ids:    [int, ...]            (optional)
        day_of_week:  0..6                  (optional — schedule)
        start_time:   HH:MM                 (optional — schedule)
        end_time:     HH:MM                 (optional — schedule;
                      if omitted but tracks given, computed from total duration)

    Returns: {show, playlist, schedule, total_duration_seconds}.
    """
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        d = request.data
        station_slug = d.get('station')
        name = (d.get('name') or '').strip()
        if not station_slug or not name:
            return Response({'detail': 'station and name are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        station = _resolve_station(station_slug)

        # 1) Resolve track IDs (preserve client-side order)
        raw_ids = d.get('track_ids') or []
        track_ids: list[int] = []
        for tid in raw_ids:
            try:
                track_ids.append(int(tid))
            except (TypeError, ValueError):
                continue
        existing_tracks = AudioTrack.objects.in_bulk(track_ids)
        # Preserve insertion order, dedupe
        ordered_tracks: list[AudioTrack] = []
        seen = set()
        for tid in track_ids:
            if tid in existing_tracks and tid not in seen:
                seen.add(tid)
                ordered_tracks.append(existing_tracks[tid])

        total_seconds = sum(int(t.duration_seconds or 0) for t in ordered_tracks)

        # 2) Auto-create a playlist if any tracks were chosen
        playlist = None
        if ordered_tracks:
            today = timezone.localdate()
            playlist = Playlist.objects.create(
                title=f'{name} mix',
                date=today,
                station=station,
                status=PlaylistStatus.ACTIVE,
            )
            for i, tr in enumerate(ordered_tracks, 1):
                PlaylistItem.objects.create(playlist=playlist, track=tr, order=i)
            playlist.refresh_from_db()

        # 3) Create the show
        slug = (slugify(name) or 'show')[:120]
        candidate, n = slug, 2
        while Show.objects.filter(slug=candidate).exists():
            candidate = f'{slug}-{n}'
            n += 1
        show = Show.objects.create(
            name=name, slug=candidate,
            description=d.get('description', ''),
            color=d.get('color', '#10b981'),
            station=station,
            host=request.user,
            playlist=playlist,
        )

        # 4) Optional weekly schedule
        schedule = None
        day = d.get('day_of_week')
        start = d.get('start_time')
        end = d.get('end_time')
        if day is not None and start:
            try:
                start_t = _parse_time(start)
            except ValueError as exc:
                return Response({'detail': f'start_time: {exc}'},
                                status=status.HTTP_400_BAD_REQUEST)
            if end:
                try:
                    end_t = _parse_time(end)
                except ValueError as exc:
                    return Response({'detail': f'end_time: {exc}'},
                                    status=status.HTTP_400_BAD_REQUEST)
            elif total_seconds > 0:
                # Auto-compute end_time from playlist total duration
                from datetime import datetime, timedelta
                base = datetime.combine(timezone.localdate(), start_t)
                end_t = (base + timedelta(seconds=total_seconds)).time()
            else:
                end_t = None

            if end_t is not None:
                try:
                    day_int = int(day)
                except (TypeError, ValueError):
                    day_int = -1
                if day_int in WeekDay.values:
                    schedule = ShowSchedule.objects.create(
                        show=show, day_of_week=day_int,
                        start_time=start_t, end_time=end_t,
                    )

        return Response({
            'show': _serialize_show(show),
            'playlist': {
                'id': playlist.id, 'title': playlist.title,
                'item_count': playlist.items.count(),
                'total_duration': playlist.total_duration,
            } if playlist else None,
            'schedule': _serialize_schedule(schedule) if schedule else None,
            'total_duration_seconds': total_seconds,
        }, status=status.HTTP_201_CREATED)


# ───────── Now / upcoming ─────────

class CurrentShowView(APIView):
    """GET /api/radio/dj/schedule/current/?station=<slug>"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        slug = request.GET.get('station')
        if not slug:
            return Response({'detail': 'station is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        station = _resolve_station(slug)

        sched = scheduler_service.current_schedule(station)
        upcoming = scheduler_service.upcoming_schedules(station, limit=6)

        return Response({
            'now': _serialize_schedule(sched) if sched else None,
            'upcoming': [_serialize_schedule(s) for s in upcoming],
            'recent_episodes': [
                {
                    'id': e.id,
                    'show_id': e.show_id,
                    'show_name': e.show.name,
                    'started_at': e.started_at,
                    'ended_at': e.ended_at,
                    'duration_seconds': e.duration_seconds,
                    'listener_peak': e.listener_peak,
                }
                for e in (
                    ShowEpisode.objects
                    .select_related('show')
                    .filter(station=station)
                    .order_by('-started_at')[:10]
                )
            ],
        })
