"""Firebase Cloud Messaging HTTP v1 client.

We deliberately keep this minimal — one function `send(token, title, body, data)`
and a batch helper. OAuth2 access tokens are obtained via google-auth using
the configured service-account JSON file.

If FCM credentials aren't configured, `is_configured()` returns False and
the campaign-runner Celery task short-circuits (records every delivery as
failed with reason="fcm_not_configured") so admins know to set it up.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Iterable, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_FCM_URL_TEMPLATE = 'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
_SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

_credentials = None
_credentials_lock = threading.Lock()


@dataclass
class SendResult:
    ok: bool
    message_id: str = ''
    error: str = ''


def is_configured() -> bool:
    return bool(settings.FCM_PROJECT_ID and settings.FCM_SERVICE_ACCOUNT_FILE)


def _get_credentials():
    global _credentials
    if _credentials is not None:
        return _credentials
    with _credentials_lock:
        if _credentials is not None:
            return _credentials
        try:
            from google.oauth2 import service_account  # noqa: WPS433
        except ImportError:
            logger.error('google-auth library not installed (pip install google-auth)')
            return None

        try:
            _credentials = service_account.Credentials.from_service_account_file(
                settings.FCM_SERVICE_ACCOUNT_FILE,
                scopes=_SCOPES,
            )
        except Exception as exc:
            logger.error('FCM credentials load failed: %s', exc)
            return None
    return _credentials


def _refresh_token() -> Optional[str]:
    creds = _get_credentials()
    if creds is None:
        return None
    if not creds.valid:
        try:
            from google.auth.transport import requests as gauth_requests  # noqa: WPS433
            creds.refresh(gauth_requests.Request())
        except Exception as exc:
            logger.error('FCM credentials refresh failed: %s', exc)
            return None
    return creds.token


def send(
    *,
    token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    image_url: Optional[str] = None,
    timeout: float = 5.0,
) -> SendResult:
    if not is_configured():
        return SendResult(ok=False, error='fcm_not_configured')

    access_token = _refresh_token()
    if not access_token:
        return SendResult(ok=False, error='fcm_token_unavailable')

    payload: dict = {
        'message': {
            'token': token,
            'notification': {
                'title': title,
                'body': body,
            },
        },
    }
    if image_url:
        payload['message']['notification']['image'] = image_url
    if data:
        # FCM v1 requires string keys/values
        payload['message']['data'] = {str(k): str(v) for k, v in data.items()}

    url = _FCM_URL_TEMPLATE.format(project_id=settings.FCM_PROJECT_ID)
    try:
        resp = requests.post(
            url,
            headers={'Authorization': f'Bearer {access_token}',
                     'Content-Type': 'application/json; UTF-8'},
            json=payload,
            timeout=timeout,
        )
    except Exception as exc:
        return SendResult(ok=False, error=f'transport_error: {exc}')

    if resp.status_code == 200:
        return SendResult(ok=True, message_id=resp.json().get('name', ''))

    err = ''
    try:
        err = resp.json().get('error', {}).get('message') or resp.text
    except Exception:
        err = resp.text
    return SendResult(ok=False, error=f'http_{resp.status_code}: {err}')


def send_batch(items: Iterable[dict], *, throttle_per_sec: int = 50) -> list[SendResult]:
    """Send many messages serially, respecting a per-second cap.

    `items` is an iterable of dicts matching `send()` kwargs.
    """
    results: list[SendResult] = []
    interval = 1.0 / max(1, throttle_per_sec)
    for item in items:
        results.append(send(**item))
        time.sleep(interval)
    return results
