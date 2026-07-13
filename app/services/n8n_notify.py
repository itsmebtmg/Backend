import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.models import Order, OrderItem

logger = logging.getLogger(__name__)

LUMEA_SKU = "LUMEA_PLUS_100ML"
GEL_SKU = "SOLYRA_PURE_200ML"
SUN_SKU = "SUN_PROTECT_PLUS_50ML"


def is_whatsapp_upsell_eligible(order: Order, items: list[OrderItem]) -> bool:
    """Lumea+ only at 239 MAD without site upsell — offer Gel +110 + free Ecran on WhatsApp."""
    if order.upsell_accepted or order.total_mad != 239 or len(items) != 1:
        return False
    item = items[0]
    return item.sku == LUMEA_SKU and item.product_slug == "lumea-plus"


def build_n8n_order_payload(order: Order, items: list[OrderItem]) -> dict:
    items_payload = [
        {
            "sku": item.sku,
            "product_slug": item.product_slug,
            "name": item.name,
            "quantity": item.quantity,
            "unit_price_mad": item.unit_price_mad,
            "is_free_gift": item.is_free_gift,
        }
        for item in items
    ]
    items_text = " | ".join(
        f"{item['name']} x{item['quantity']} "
        f"{'FREE' if item['is_free_gift'] else str(item['unit_price_mad']) + ' MAD'}"
        for item in items_payload
    )
    return {
        "event": "order_finalized",
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "phone_e164": order.phone_e164,
        "phone_local": order.phone_local,
        "city": order.city,
        "address": order.address,
        "items": items_payload,
        "items_text": items_text,
        "subtotal_mad": order.subtotal_mad,
        "shipping_mad": order.shipping_mad,
        "total_mad": order.total_mad,
        "upsell_accepted": order.upsell_accepted,
        "whatsapp_upsell_eligible": is_whatsapp_upsell_eligible(order, items),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
async def notify_n8n_order(payload: dict) -> None:
    if not settings.enable_n8n_whatsapp or not settings.n8n_order_webhook_url:
        return

    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        response = await client.post(settings.n8n_order_webhook_url, json=payload)
        if response.status_code >= 400:
            logger.warning("n8n_notify_failed", extra={"status": response.status_code})
            response.raise_for_status()
