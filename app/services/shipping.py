"""Delivery/shipping abstraction.

No shipping-company API is wired in yet, so the only provider today is
`ManualShippingProvider`: an admin sets delivery_status by hand from the
dashboard (see PATCH /v1/admin/orders/{order_number}/shipment).

Once you have the shipping company's API, implement a new provider here
(e.g. `AmanaShippingProvider`) that:
  - creates a shipment / fetches a tracking number when an order is confirmed
  - exposes a `sync_status(shipment)` method (called from a webhook route or
    a periodic job) that updates `delivery_status`, `shipped_at`,
    `delivered_at` from the carrier's response.
Then flip `SHIPPING_PROVIDER` in the environment and select it in
`get_shipping_provider()` below — no other code needs to change.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import settings
from app.db.models import Shipment


class ShippingProvider(Protocol):
    name: str

    async def sync_status(self, shipment: Shipment) -> None:
        """Refresh delivery_status/shipped_at/delivered_at from the carrier.
        No-op for the manual provider; a real provider would call the
        carrier's API here.
        """
        ...


class ManualShippingProvider:
    name = "manual"

    async def sync_status(self, shipment: Shipment) -> None:
        return None


def get_shipping_provider() -> ShippingProvider:
    # Only "manual" exists today; extend with an if/elif once a real
    # provider is implemented, keyed off settings.shipping_provider.
    return ManualShippingProvider()
