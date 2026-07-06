import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
async def sync_order_to_sheet(order_payload: dict) -> None:
    if not settings.enable_google_sheets or not settings.google_sheets_webhook_url:
        return

    # Flat, simple payload matching the columns expected by
    # docs/google-apps-script/orders-webhook.js. No secret required: the
    # webhook URL itself (Apps Script "Anyone" access) is the only guard.
    payload = {
        "date": order_payload["sheet_date"],
        "order_id": order_payload["sheet_order_id"],
        "country": order_payload["sheet_country"],
        "name": order_payload["sheet_name"],
        "phone": order_payload["sheet_phone"],
        "product": order_payload["sheet_product"],
        "quantity": order_payload["sheet_quantity"],
        "total_price": order_payload["sheet_total_price"],
        "currency": order_payload["sheet_currency"],
        "status": order_payload["sheet_status"],
    }
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        response = await client.post(settings.google_sheets_webhook_url, json=payload)
        if response.status_code >= 400:
            logger.warning("sheet_sync_failed", extra={"status": response.status_code})
            response.raise_for_status()

        # Apps Script's ContentService almost always answers with HTTP 200
        # even when the script itself failed, so a 2xx status code alone is
        # not proof of success. Check the JSON body's "ok" flag too.
        try:
            body = response.json()
        except ValueError:
            body = None

        if body is not None and body.get("ok") is False:
            logger.warning("sheet_sync_failed", extra={"body": body})
            raise RuntimeError(f"sheet webhook returned ok=false: {body}")
