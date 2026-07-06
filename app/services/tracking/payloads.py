from datetime import datetime, timezone

from app.services.hashing import sha256_hex


def build_contents(items: list[dict]) -> list[dict]:
    return [
        {
            "id": item["sku"],
            "quantity": item["quantity"],
            "item_price": item["unit_price_mad"],
        }
        for item in items
    ]


def meta_purchase_payload(order: dict, phone: dict) -> dict:
    event_time = int(datetime.now(tz=timezone.utc).timestamp())
    return {
        "event_name": "Purchase",
        "event_time": event_time,
        "event_id": order["event_id"],
        "action_source": "website",
        "event_source_url": order.get("landing_url") or "https://solyra.ma",
        "user_data": {
            "ph": [sha256_hex(phone["digits_international"])],
            "client_ip_address": order.get("client_ip"),
            "client_user_agent": order.get("client_user_agent"),
            "fbp": order.get("fbp"),
            "fbc": order.get("fbc"),
        },
        "custom_data": {
            "currency": "MAD",
            "value": order["total_mad"],
            "order_id": order["order_number"],
            "content_type": "product",
            "content_ids": [item["sku"] for item in order["items"]],
            "contents": build_contents(order["items"]),
        },
    }


def tiktok_purchase_payload(order: dict, phone: dict, pixel_code: str) -> dict:
    return {
        "pixel_code": pixel_code,
        "event": "CompletePayment",
        "event_id": order["event_id"],
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "context": {
            "page": {"url": order.get("landing_url") or "https://solyra.ma"},
            "user": {
                "phone_number": sha256_hex(phone["e164"]),
                "ttp": order.get("ttp"),
                "ttclid": order.get("ttclid"),
                "ip": order.get("client_ip"),
                "user_agent": order.get("client_user_agent"),
            },
        },
        "properties": {
            "currency": "MAD",
            "value": order["total_mad"],
            "content_type": "product",
            "order_id": order["order_number"],
            "contents": [
                {
                    "content_id": item["sku"],
                    "content_name": item["name"],
                    "quantity": item["quantity"],
                    "price": item["unit_price_mad"],
                }
                for item in order["items"]
            ],
        },
    }


def snap_purchase_payload(order: dict, phone: dict) -> dict:
    return {
        "event_name": "PURCHASE",
        "event_time": int(datetime.now(tz=timezone.utc).timestamp() * 1000),
        "event_id": order["event_id"],
        "event_source_url": order.get("landing_url") or "https://solyra.ma",
        "user_data": {
            "ph": [sha256_hex(phone["digits_international"])],
            "client_ip_address": order.get("client_ip"),
            "client_user_agent": order.get("client_user_agent"),
        },
        "custom_data": {
            "currency": "MAD",
            "value": order["total_mad"],
            "order_id": order["order_number"],
            "content_ids": [item["sku"] for item in order["items"]],
            "contents": build_contents(order["items"]),
        },
    }
