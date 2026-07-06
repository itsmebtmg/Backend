import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
async def sync_order_to_sheet(order_payload: dict) -> None:
    if not settings.enable_google_sheets or not settings.google_sheets_webhook_url:
        return

    payload = {
        "secret": settings.google_sheets_webhook_secret,
        "type": "order_created",
        "order": order_payload,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.google_sheets_webhook_url, json=payload)
        if response.status_code >= 400:
            logger.warning("sheet_sync_failed", extra={"status": response.status_code})
            response.raise_for_status()
