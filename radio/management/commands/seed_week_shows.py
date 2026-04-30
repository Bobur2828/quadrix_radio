"""Seed a full weekly schedule of shows for a station.

Usage:
    python manage.py seed_week_shows
    python manage.py seed_week_shows --station quadrix --reset

Distributes the existing AudioTracks across 9 themed shows that span the
whole week (workday programming + weekend programming). Each show gets a
shuffled mix of 8-12 tracks. Tracks are reused across shows because the
library is small.

Run `import_audio mp3/` first to populate the library.
"""

from __future__ import annotations

import random
from datetime import time
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from radio.models import (
    AudioTrack, Playlist, PlaylistItem, PlaylistStatus,
    RadioStation, Show, ShowSchedule,
)


# (name, color, description, [(day_of_week, start, end), ...])
SHOWS = [
    (
        'Morning Drive', '#f59e0b',
        'Energetic morning show — wake up tracks for the commute.',
        [(d, '06:00', '09:00') for d in range(0, 5)],   # Mon-Fri
    ),
    (
        'Mid-Morning Mix', '#10b981',
        'Smooth mid-morning music for the office grind.',
        [(d, '09:00', '12:00') for d in range(0, 5)],
    ),
    (
        'Lunch Break', '#3b82f6',
        'Lunch hour — chill but upbeat.',
        [(d, '12:00', '14:00') for d in range(0, 5)],
    ),
    (
        'Afternoon Mix', '#8b5cf6',
        'Afternoon programming — keeps the energy steady.',
        [(d, '14:00', '18:00') for d in range(0, 5)],
    ),
    (
        'Evening Drive', '#ec4899',
        'Drive-time hits as listeners head home.',
        [(d, '18:00', '22:00') for d in range(0, 5)],
    ),
    (
        'Late Night', '#475569',
        'Late-night atmosphere for night drivers.',
        [(d, '22:00', '02:00') for d in range(0, 5)],   # crosses midnight
    ),
    (
        'Weekend Brunch', '#06b6d4',
        'Saturday & Sunday brunch — relaxed weekend vibes.',
        [(d, '09:00', '13:00') for d in (5, 6)],         # Sat, Sun
    ),
    (
        'Weekend Party', '#ef4444',
        'Weekend afternoon party — bangers all the way.',
        [(d, '13:00', '19:00') for d in (5, 6)],
    ),
    (
        'Weekend Night', '#6366f1',
        'Saturday/Sunday night vibes.',
        [(d, '19:00', '23:00') for d in (5, 6)],
    ),
]


class Command(BaseCommand):
    help = 'Auto-create a full weekly programming schedule.'

    def add_arguments(self, parser):
        parser.add_argument('--station', default=None,
                            help='Station slug (default: default station)')
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing shows on this station first')

    @transaction.atomic
    def handle(self, *args, **opts):
        station = self._get_station(opts.get('station'))
        self.stdout.write(self.style.NOTICE(f'Station: {station}'))

        if opts['reset']:
            n_shows = Show.objects.filter(station=station).count()
            n_pls = Playlist.objects.filter(
                station=station, title__endswith=' mix',
            ).count()
            Show.objects.filter(station=station).delete()
            Playlist.objects.filter(
                station=station, title__endswith=' mix',
            ).delete()
            self.stdout.write(self.style.WARNING(
                f'Reset: removed {n_shows} show(s) and {n_pls} auto-playlist(s).'
            ))

        tracks = list(AudioTrack.objects.filter(
            duration_seconds__gt=0,
        ).extra(
            where=["LOWER(audio_file) LIKE '%%.mp3'"],
        ).order_by('id'))
        if not tracks:
            raise CommandError(
                'No usable tracks found. Run `python manage.py import_audio mp3/` first.'
            )
        self.stdout.write(f'Library: {len(tracks)} usable MP3 track(s).')

        today = timezone.localdate()
        random.seed(42)

        for name, color, description, slots in SHOWS:
            slug = self._unique_slug(name)

            # Compute the slot's duration in seconds (handle midnight wrap).
            slot_seconds = self._slot_seconds(slots[0])

            # Fill the playlist with enough tracks (repeats allowed) so its
            # total duration ≥ slot duration. Shuffle so the order varies.
            picked = self._fill_to_duration(tracks, slot_seconds)

            playlist = Playlist.objects.create(
                title=f'{name} mix', date=today,
                station=station, status=PlaylistStatus.ACTIVE,
            )
            PlaylistItem.objects.bulk_create([
                PlaylistItem(playlist=playlist, track=t, order=j)
                for j, t in enumerate(picked, 1)
            ])
            total_dur = sum(t.duration_seconds for t in picked)
            Playlist.objects.filter(pk=playlist.pk).update(total_duration=total_dur)
            playlist.total_duration = total_dur

            show = Show.objects.create(
                name=name, slug=slug,
                description=description,
                color=color,
                station=station, playlist=playlist,
            )
            ShowSchedule.objects.bulk_create([
                ShowSchedule(
                    show=show, day_of_week=d,
                    start_time=time.fromisoformat(start),
                    end_time=time.fromisoformat(end),
                )
                for d, start, end in slots
            ])

            slot_min = slot_seconds // 60
            self.stdout.write(
                f'  ✓ {name:18s}  '
                f'{len(slots)}× {slot_min}-min slots  ·  '
                f'{len(picked)} tracks ({total_dur//60} min, '
                f'{total_dur//slot_seconds}× slot length)'
            )

        total = Show.objects.filter(station=station).count()
        slots_total = ShowSchedule.objects.filter(show__station=station).count()
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Station "{station.slug}" now has {total} show(s) '
            f'and {slots_total} weekly slot(s).'
        ))
        self.stdout.write(
            'Open the dashboard 📡 Shows tab to see the weekly grid.'
        )

    # ----- helpers -----

    def _get_station(self, slug: Optional[str]) -> RadioStation:
        if slug:
            try:
                return RadioStation.objects.get(slug=slug)
            except RadioStation.DoesNotExist as exc:
                raise CommandError(f'Station "{slug}" not found.') from exc
        station = (
            RadioStation.objects.filter(is_default=True).first()
            or RadioStation.objects.first()
        )
        if not station:
            raise CommandError('No station exists. Create one first.')
        return station

    def _unique_slug(self, name: str) -> str:
        base = slugify(name)[:120] or 'show'
        slug = base
        i = 2
        while Show.objects.filter(slug=slug).exists():
            slug = f'{base}-{i}'
            i += 1
        return slug

    @staticmethod
    def _slot_seconds(slot) -> int:
        """How many seconds does this (day, start, end) slot last?"""
        _, start, end = slot
        sh, sm = (int(x) for x in start.split(':'))
        eh, em = (int(x) for x in end.split(':'))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        if end_min <= start_min:
            end_min += 24 * 60
        return (end_min - start_min) * 60

    @staticmethod
    def _fill_to_duration(tracks: list, target_seconds: int) -> list:
        """Pick tracks (with repeats) until total duration ≥ target.

        Shuffles the pool every full pass so the same artist doesn't run
        back-to-back across cycles.
        """
        if not tracks or target_seconds <= 0:
            return list(tracks)
        result = []
        total = 0
        pool = list(tracks)
        random.shuffle(pool)
        idx = 0
        while total < target_seconds:
            track = pool[idx % len(pool)]
            result.append(track)
            total += track.duration_seconds or 180
            idx += 1
            if idx % len(pool) == 0:
                random.shuffle(pool)
        return result
