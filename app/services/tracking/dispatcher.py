import logging

import httpx

from app.core.config import settings
from app.services.tracking.payloads import (
    meta_purchase_payload,
    snap_purchase_payload,
    tiktok_purchase_payload,
)

logger = logging.getLogger(__name__)


async def send_purchase_events(order: dict, phone: dict) -> list[dict]:
    if not settings.enable_capi:
        return []

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=12) as client:
        if settings.meta_pixel_id and settings.meta_access_token:
            payload = {"data": [meta_purchase_payload(order, phone)]}
            if settings.meta_test_event_code:
                payload["test_event_code"] = settings.meta_test_event_code
            url = (
                f"https://graph.facebook.com/v20.0/{settings.meta_pixel_id}/events"
                f"?access_token={settings.meta_access_token}"
            )
            results.append(await _post(client, "meta", "Purchase", url, payload))

        if settings.tiktok_pixel_code and settings.tiktok_access_token:
            payload = tiktok_purchase_payload(order, phone, settings.tiktok_pixel_code)
            if settings.tiktok_test_event_code:
                payload["test_event_code"] = settings.tiktok_test_event_code
            # TikTok endpoint versions change; keep the exact URL configurable in future if needed.
            url = "https://business-api.tiktok.com/open_api/v1.3/pixel/track/"
            headers = {"Access-Token": settings.tiktok_access_token}
            results.append(await _post(client, "tiktok", "CompletePayment", url, payload, headers))

        if settings.snap_pixel_id and settings.snap_access_token:
            payload = snap_purchase_payload(order, phone)
            if settings.snap_test_event_code:
                payload["test_event_code"] = settings.snap_test_event_code
            # Snap has multiple CAPI versions; this endpoint should be confirmed in Events Manager.
            url = f"https://tr.snapchat.com/v3/{settings.snap_pixel_id}/events"
            headers = {"Authorization": f"Bearer {settings.snap_access_token}"}
            results.append(await _post(client, "snapchat", "PURCHASE", url, payload, headers))

    return results


async def _post(
    client: httpx.AsyncClient,
    platform: str,
    event_name: str,
    url: str,
    payload: dict,
    headers: dict | None = None,
) -> dict:
    try:
        response = await client.post(url, json=payload, headers=headers)
        return {
            "platform": platform,
            "event_name": event_name,
            "payload": payload,
            "response_status": response.status_code,
            "response_body": response.text[:2000],
            "success": response.status_code < 400,
        }
    except Exception as exc:  # noqa: BLE001 - record all outbound failures
        logger.exception("capi_send_failed", extra={"platform": platform})
        return {
            "platform": platform,
            "event_name": event_name,
            "payload": payload,
            "response_status": None,
            "response_body": str(exc),
            "success": False,
        }
