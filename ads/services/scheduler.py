"""Pick the next ad to play for a given station/region/segment.

Selection uses weighted-random across all eligible ads, where eligibility
means: status=active, within date window, daily-cap not exhausted,
total-cap not exhausted, region/segment match (or unrestricted).
"""

from __future__ import annotations

import logging
import random
from datetime import timedelta
from typing import Optional

from django.db.models import Count, Q
from django.utils import timezone

from ads.models import AdPlay, AdStatus, SponsoredAd
from radio.models import RadioStation

logger = logging.getLogger(__name__)


def _eligible_ads_qs(station: RadioStation, *,
                     region_id: Optional[int],
                     segment_id: Optional[int]):
    now = timezone.now()
    qs = SponsoredAd.objects.filter(
        status=AdStatus.ACTIVE,
        start_at__lte=now,
        end_at__gte=now,
    )

    if region_id:
        qs = qs.filter(Q(target_regions__isnull=True) | Q(target_regions__id=region_id))
    else:
        qs = qs.filter(target_regions__isnull=True)

    if segment_id:
        qs = qs.filter(Q(target_segments__isnull=True) | Q(target_segments__id=segment_id))

    return qs.distinct()


def _filter_by_caps(candidates):
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    counts_today = dict(
        AdPlay.objects
        .filter(started_at__gte=today_start, ad_id__in=[c.id for c in candidates])
        .values_list('ad_id')
        .annotate(n=Count('id'))
    )

    out = []
    for ad in candidates:
        if ad.max_total_plays and ad.play_count_total >= ad.max_total_plays:
            continue
        if ad.max_plays_per_day:
            if counts_today.get(ad.id, 0) >= ad.max_plays_per_day:
                continue
        out.append(ad)
    return out


def pick_next_ad(station: RadioStation, *,
                 region_id: Optional[int] = None,
                 segment_id: Optional[int] = None) -> Optional[SponsoredAd]:
    candidates = list(_eligible_ads_qs(station, region_id=region_id, segment_id=segment_id))
    if not candidates:
        return None

    candidates = _filter_by_caps(candidates)
    if not candidates:
        return None

    weights = [max(1, ad.weight) for ad in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def log_ad_play(*, ad: SponsoredAd, station: RadioStation,
                session_id: Optional[int] = None,
                region_id: Optional[int] = None,
                completed: bool = False,
                duration_seconds: int = 0) -> AdPlay:
    play = AdPlay.objects.create(
        ad=ad,
        station=station,
        session_id=session_id,
        region_id=region_id,
        completed=completed,
        duration_seconds=duration_seconds,
    )
    SponsoredAd.objects.filter(pk=ad.pk).update(
        play_count_total=ad.play_count_total + 1,
    )
    return play


def burn_out_expired() -> int:
    """Mark ads whose end_at has passed as expired. Returns count."""
    now = timezone.now()
    return SponsoredAd.objects.filter(
        status=AdStatus.ACTIVE, end_at__lt=now,
    ).update(status=AdStatus.EXPIRED)
