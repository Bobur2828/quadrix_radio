"""IP → country/state → Region resolver.

Three layers:
  1. If MaxMind GeoLite2-City.mmdb is available, look up country + subdivision.
  2. Map subdivision (US-TX, US-CA, ...) to a Region via RegionStateMapping.
  3. Otherwise return (None, None).

The resolver is intentionally lazy: if `geoip2` isn't installed or the DB
isn't configured, callers still get a result — just without a region.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.cache import cache

from analytics.models import Region, RegionStateMapping

logger = logging.getLogger(__name__)

_reader = None
_reader_lock = threading.Lock()


@dataclass
class GeoResult:
    country: str = ''
    state_code: str = ''
    region: Optional[Region] = None


def _get_reader():
    global _reader
    if _reader is not None:
        return _reader
    path = getattr(settings, 'GEOIP_DATABASE', '') or ''
    if not path:
        return None
    with _reader_lock:
        if _reader is not None:
            return _reader
        try:
            import geoip2.database  # noqa: WPS433
            _reader = geoip2.database.Reader(path)
        except Exception as exc:
            logger.warning('GeoIP reader unavailable (%s): %s', path, exc)
            _reader = False  # cache failure
    return _reader if _reader else None


def resolve(ip_address: Optional[str]) -> GeoResult:
    if not ip_address:
        return GeoResult()

    cache_key = f'geo:ip:{ip_address}'
    cached = cache.get(cache_key)
    if cached is not None:
        country, state_code, region_id = cached
        region = Region.objects.filter(pk=region_id).first() if region_id else None
        return GeoResult(country=country, state_code=state_code, region=region)

    reader = _get_reader()
    country = ''
    state_code = ''
    if reader is not None:
        try:
            resp = reader.city(ip_address)
            country = (resp.country.iso_code or '').upper()
            subs = resp.subdivisions.most_specific
            sub_code = (subs.iso_code or '').upper() if subs else ''
            if country and sub_code:
                state_code = f'{country}-{sub_code}'
        except Exception as exc:
            logger.debug('GeoIP lookup failed for %s: %s', ip_address, exc)

    region = None
    if state_code:
        mapping = (
            RegionStateMapping.objects
            .select_related('region')
            .filter(state_code=state_code)
            .first()
        )
        if mapping is not None:
            region = mapping.region

    cache.set(cache_key, (country, state_code, region.id if region else None), 6 * 3600)
    return GeoResult(country=country, state_code=state_code, region=region)
