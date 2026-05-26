import logging
import secrets
from datetime import timedelta
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import RedirectResponse

from app import crud
from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.models import User

logger = logging.getLogger(__name__)

ErrorCode = Literal[
    "state_mismatch",
    "missing_state",
    "unverified_email",
    "google_unreachable",
    "access_denied",
]

router = APIRouter(prefix="/auth/google", tags=["google-auth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_OAUTH_STATE_COOKIE = "oauth_state"


def _google_redirect_uri() -> str:
    return f"{settings.BACKEND_HOST}{settings.API_V1_STR}/auth/google/callback"


def _redirect_error(code: ErrorCode) -> RedirectResponse:
    response = RedirectResponse(
        url=f"{settings.FRONTEND_HOST}/auth/callback?error={code}",
        status_code=302,
    )
    response.delete_cookie(key=_OAUTH_STATE_COOKIE)
    return response


@router.get("/login")
def google_login() -> RedirectResponse:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured.")

    state = secrets.token_urlsafe(32)
    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    })
    auth_url = f"{_GOOGLE_AUTH_URL}?{params}"

    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key=_OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT != "local",
        max_age=300,
    )
    return response


@router.get("/callback")
def google_callback(
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google login is not configured.")

    if error:
        return _redirect_error("access_denied")

    if not oauth_state:
        return _redirect_error("missing_state")

    if not state or state != oauth_state:
        return _redirect_error("state_mismatch")

    try:
        with httpx.Client() as client:
            token_response = client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": _google_redirect_uri(),
                    "grant_type": "authorization_code",
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("Google token exchange transport error: %s", exc)
        return _redirect_error("google_unreachable")

    if token_response.status_code != 200 or not token_response.json().get("access_token"):
        logger.warning("Google token exchange failed: status=%s body=%s", token_response.status_code, token_response.text)
        return _redirect_error("google_unreachable")

    access_token = token_response.json()["access_token"]

    try:
        with httpx.Client() as client:
            userinfo_response = client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        logger.warning("Google userinfo fetch transport error: %s", exc)
        return _redirect_error("google_unreachable")

    if userinfo_response.status_code != 200:
        logger.warning("Google userinfo fetch failed: status=%s body=%s", userinfo_response.status_code, userinfo_response.text)
        return _redirect_error("google_unreachable")

    userinfo = userinfo_response.json()

    if not userinfo.get("email_verified"):
        return _redirect_error("unverified_email")

    email: str = userinfo["email"]
    full_name: str | None = userinfo.get("name")

    db_user = crud.get_user_by_email(session=session, email=email)
    if not db_user:
        db_user = User(
            email=email,
            full_name=full_name,
            is_active=True,
            is_superuser=False,
            hashed_password=None,
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

    jwt = security.create_access_token(
        db_user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    redirect_url = f"{settings.FRONTEND_HOST}/auth/callback?access_token={jwt}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.delete_cookie(key=_OAUTH_STATE_COOKIE)
    return response
