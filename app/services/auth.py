"""Admin authentication: a single shared username/password pair from env
vars (ADMIN_USERNAME / ADMIN_PASSWORD), backed by a signed JWT stored in an
httpOnly cookie. No admin-users table — this is intentionally simple since
there's only ever one admin login, as requested.
"""

from __future__ import annotations

import hmac
import time
from dataclasses import dataclass

import jwt
from fastapi import Cookie, HTTPException, status

from app.core.config import settings

_ALGORITHM = "HS256"

# Naive in-memory login rate limiter: {ip: [timestamps]}. Fine for a
# single-process deployment; swap for Redis if you scale out horizontally.
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 15 * 60


class TooManyLoginAttempts(Exception):
    pass


def check_login_rate_limit(ip: str) -> None:
    now = time.monotonic()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < _WINDOW_SECONDS]
    if len(attempts) >= _MAX_ATTEMPTS:
        raise TooManyLoginAttempts()
    _login_attempts[ip] = attempts


def record_login_attempt(ip: str) -> None:
    _login_attempts.setdefault(ip, []).append(time.monotonic())


def clear_login_attempts(ip: str) -> None:
    _login_attempts.pop(ip, None)


def verify_admin_credentials(username: str, password: str) -> bool:
    valid_username = hmac.compare_digest(username, settings.admin_username)
    valid_password = hmac.compare_digest(password, settings.admin_password)
    return valid_username and valid_password


def create_session_token(username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_ALGORITHM)


@dataclass(frozen=True)
class AdminSession:
    username: str


def decode_session_token(token: str) -> AdminSession | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return AdminSession(username=payload.get("sub", ""))


async def require_admin(
    session_token: str | None = Cookie(default=None, alias=settings.admin_cookie_name),
) -> AdminSession:
    """FastAPI dependency: 401s unless a valid admin session cookie is present."""
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    session = decode_session_token(session_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")
    return session
