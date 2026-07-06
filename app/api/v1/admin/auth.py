from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import settings
from app.schemas.admin import LoginIn, LoginOut, MeOut
from app.services.auth import (
    AdminSession,
    TooManyLoginAttempts,
    check_login_rate_limit,
    clear_login_attempts,
    create_session_token,
    record_login_attempt,
    require_admin,
    verify_admin_credentials,
)

router = APIRouter(prefix="/auth", tags=["admin-auth"])


@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn, request: Request, response: Response) -> LoginOut:
    client_ip = request.client.host if request.client else "unknown"

    try:
        check_login_rate_limit(client_ip)
    except TooManyLoginAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too_many_attempts"
        ) from exc

    if not verify_admin_credentials(payload.username, payload.password):
        record_login_attempt(client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    clear_login_attempts(client_ip)
    token = create_session_token(payload.username)
    response.set_cookie(
        key=settings.admin_cookie_name,
        value=token,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    # Returning the raw token lets the Next.js frontend (a different domain,
    # e.g. solyra.ma vs api.solyra.ma) store it in its own first-party cookie
    # and forward it on server-to-server calls, since a Set-Cookie from a
    # cross-domain API response is never visible to that other domain.
    return LoginOut(username=payload.username, token=token)


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(key=settings.admin_cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeOut)
async def me(session: AdminSession = Depends(require_admin)) -> MeOut:
    return MeOut(username=session.username)
