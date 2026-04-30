"""DJ live mic ingest over WebSocket — lowest-latency path.

Browser opens
    ws://<host>/ws/dj/live/<broadcast_id>/?key=<stream_key>&fmt=webm
and pushes binary frames as `MediaRecorder.ondataavailable` fires.
Each frame is fed to ffmpeg.stdin instantly — no per-chunk HTTP overhead,
no middleware, no DB lookup, single TCP connection.

Compared to the HTTP upload path:
  - 1 TCP/TLS handshake total (vs 1 per 100 ms chunk)
  - No CSRF / Django middleware overhead
  - One DB lookup at connect time (cached on the consumer)
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from radio.models import LiveBroadcast, LiveStatus
from radio.services import broadcaster as broadcaster_service
from radio.services import live_session as live_session_service

logger = logging.getLogger(__name__)


class LiveUploadConsumer(AsyncWebsocketConsumer):
    """One DJ → server WebSocket per live broadcast."""

    async def connect(self):
        broadcast_id = int(self.scope['url_route']['kwargs']['broadcast_id'])
        qs = parse_qs(self.scope.get('query_string', b'').decode())
        key = (qs.get('key') or [''])[0]
        fmt = (qs.get('fmt') or ['webm'])[0].lower()
        if fmt not in {'webm', 'mp4', 'ogg', 'mpegts'}:
            fmt = 'webm'

        live = await self._lookup(broadcast_id, key)
        if live is None:
            await self.close(code=4403)
            return

        self.broadcast_id = broadcast_id
        self.station_id = live.station_id

        sess = live_session_service.get(broadcast_id)
        if sess is None:
            sess = await database_sync_to_async(live_session_service.get_or_create)(
                broadcast_id, input_format=fmt,
            )
            if sess is None:
                await self.close(code=4503)
                return
            broadcaster = broadcaster_service.get_for_station(self.station_id)
            broadcaster.attach_live(sess)
            logger.info('WS live attached: broadcast=%s station=%s fmt=%s',
                        broadcast_id, self.station_id, fmt)
        self.session = sess

        await self.accept()
        # Tell the client we're ready — useful for them to start the recorder.
        await self.send(text_data='{"ok":true,"event":"ready"}')

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            self.session.feed(bytes_data)
        # ignore text frames silently (could be heartbeats)

    async def disconnect(self, code):
        # Don't kill the live session here — the DJ may briefly reconnect.
        # The watchdog (15s without bytes) auto-ends if they don't return.
        pass

    @database_sync_to_async
    def _lookup(self, broadcast_id: int, key: str):
        if not key:
            return None
        try:
            return LiveBroadcast.objects.only(
                'id', 'station_id', 'stream_key', 'status',
            ).get(pk=broadcast_id, stream_key=key, status=LiveStatus.LIVE)
        except LiveBroadcast.DoesNotExist:
            return None
