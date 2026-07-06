"""Server-side geo / VPN verdicts, backing the "valid Moroccan IP, no VPN"
requirement for both click tracking and order metrics.

Uses the same MaxMind GeoIP2 City web service already used client-side in
frontend/src/app/actions/submit-order.ts. A small in-memory TTL cache avoids
re-querying MaxMind for repeat requests from the same IP within a short
window (page view + CTA click + order, all from one visitor, in a session).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from ipaddress import ip_address

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_PRIVATE_IPS = {"127.0.0.1", "::1"}


@dataclass(frozen=True)
class GeoVerdict:
    country_iso: str | None
    is_vpn: bool
    is_valid_ma: bool
    checked: bool  # False if MaxMind was not configured / call failed (fail-open)


_cache: dict[str, tuple[float, GeoVerdict]] = {}


def _is_local_ip(ip: str) -> bool:
    if ip in _PRIVATE_IPS:
        return True
    try:
        parsed = ip_address(ip)
    except ValueError:
        return False
    return parsed.is_private or parsed.is_loopback


def _cache_get(ip: str) -> GeoVerdict | None:
    entry = _cache.get(ip)
    if not entry:
        return None
    expires_at, verdict = entry
    if expires_at < time.monotonic():
        _cache.pop(ip, None)
        return None
    return verdict


def _cache_set(ip: str, verdict: GeoVerdict) -> None:
    _cache[ip] = (time.monotonic() + settings.geo_cache_ttl_seconds, verdict)
    # Cheap unbounded-growth guard; this is a best-effort cache, not a store.
    if len(_cache) > 20000:
        _cache.clear()


async def check_ip(ip: str | None) -> GeoVerdict:
    """Return the geo/VPN verdict for a client IP. Fails open (checked=False,
    is_valid_ma=True) if MaxMind isn't configured or the lookup errors out,
    so a MaxMind outage never blocks checkout or tracking — it only means
    that traffic won't be countable as "valid" until the check succeeds.
    Callers that want to *require* a positive check should look at `checked`.
    """
    if not ip or _is_local_ip(ip):
        return GeoVerdict(country_iso=None, is_vpn=False, is_valid_ma=True, checked=False)

    cached = _cache_get(ip)
    if cached is not None:
        return cached

    if not settings.maxmind_account_id or not settings.maxmind_license_key:
        return GeoVerdict(country_iso=None, is_vpn=False, is_valid_ma=True, checked=False)

    verdict = await _query_maxmind(ip)
    _cache_set(ip, verdict)
    return verdict


async def _query_maxmind(ip: str) -> GeoVerdict:
    auth = httpx.BasicAuth(settings.maxmind_account_id or "", settings.maxmind_license_key or "")
    url = f"https://geoip.maxmind.com/geoip/v2.1/city/{ip}"
    try:
        async with httpx.AsyncClient(timeout=4, auth=auth) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning("maxmind_lookup_failed", extra={"status": response.status_code, "ip": ip})
                return GeoVerdict(country_iso=None, is_vpn=False, is_valid_ma=True, checked=False)

            data = response.json()
    except Exception:  # noqa: BLE001 - never let geo lookups break the request
        logger.exception("maxmind_lookup_error", extra={"ip": ip})
        return GeoVerdict(country_iso=None, is_vpn=False, is_valid_ma=True, checked=False)

    country_iso = (data.get("country") or {}).get("iso_code")
    traits = data.get("traits") or {}
    is_vpn = bool(
        traits.get("is_anonymous_vpn")
        or traits.get("is_hosting_provider")
        or traits.get("is_public_proxy")
        or traits.get("is_tor_exit_node")
        or traits.get("is_anonymous")
    )
    is_valid_ma = country_iso == "MA" and not is_vpn

    return GeoVerdict(country_iso=country_iso, is_vpn=is_vpn, is_valid_ma=is_valid_ma, checked=True)


def client_ip_from_headers(forwarded_for: str | None, direct_ip: str | None) -> str | None:
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return direct_ip
