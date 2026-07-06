from fastapi import HTTPException

from app.schemas.orders import OrderCreate, OrderItemIn

CATALOG = {
    "LUMEA_PLUS_100ML": {"slug": "lumea-plus", "price": 239},
    "SOLYRA_PURE_200ML": {"slug": "solyra-pure", "price": 169},
    "SUN_PROTECT_PLUS_50ML": {"slug": "sun-protect-plus", "price": 169},
    "PROTOCOLE_SOLYRA": {"slug": "le-protocole-solyra", "price": 349},
}


def validate_and_price_order(payload: OrderCreate) -> tuple[list[OrderItemIn], int, int, int]:
    """Return normalized items, subtotal, discount, total in MAD."""
    items = payload.items

    if payload.offer.upsell_accepted:
        skus = {item.sku for item in items}
        required = {"LUMEA_PLUS_100ML", "SOLYRA_PURE_200ML", "SUN_PROTECT_PLUS_50ML"}
        if skus != required:
            raise HTTPException(status_code=422, detail="invalid_upsell_combination")

        normalized = []
        for item in items:
            if item.sku == "LUMEA_PLUS_100ML":
                normalized.append(item.model_copy(update={"unit_price_mad": 239, "is_free_gift": False}))
            elif item.sku == "SOLYRA_PURE_200ML":
                normalized.append(item.model_copy(update={"unit_price_mad": 110, "is_free_gift": False}))
            elif item.sku == "SUN_PROTECT_PLUS_50ML":
                normalized.append(item.model_copy(update={"unit_price_mad": 0, "is_free_gift": True}))
        return normalized, 349, 228, 349

    if len(items) == 1 and items[0].sku == "PROTOCOLE_SOLYRA":
        item = items[0].model_copy(update={"unit_price_mad": 349, "is_free_gift": False})
        return [item], 349, 228, 349

    normalized = []
    total = 0
    for item in items:
        catalog_item = CATALOG.get(item.sku)
        if not catalog_item:
            raise HTTPException(status_code=422, detail=f"unknown_sku:{item.sku}")
        price = catalog_item["price"]
        if item.is_free_gift:
            raise HTTPException(status_code=422, detail="free_gift_not_allowed_without_offer")
        normalized_item = item.model_copy(update={"unit_price_mad": price})
        normalized.append(normalized_item)
        total += price * item.quantity

    return normalized, total, 0, total
