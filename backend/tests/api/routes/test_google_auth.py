from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User
from tests.utils.utils import random_email


def _make_httpx_mock(
    token_data: dict | None = None,
    userinfo_data: dict | None = None,
    token_status: int = 200,
    userinfo_status: int = 200,
) -> MagicMock:
    """Return a mock that replaces httpx.Client for both context manager calls."""
    default_token = {"access_token": "google-access-token-123"}
    default_userinfo = {
        "email": "google-user@example.com",
        "name": "Google User",
        "email_verified": True,
    }

    mock_instance = MagicMock()
    mock_instance.post.return_value = MagicMock(
        status_code=token_status,
        json=MagicMock(return_value=token_data or default_token),
    )
    mock_instance.get.return_value = MagicMock(
        status_code=userinfo_status,
        json=MagicMock(return_value=userinfo_data or default_userinfo),
    )

    mock_cls = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_instance)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cls


def _set_state_cookie(client: TestClient, state: str) -> None:
    # Clear any previously stored oauth_state before setting the new one
    # (the module-scoped client may retain cookies from prior tests)
    client.cookies.clear()
    client.cookies.set("oauth_state", state)


def _clear_state_cookie(client: TestClient) -> None:
    client.cookies.clear()


# ---------------------------------------------------------------------------
# 6.2 — Login endpoint returns 302 with Google Location header and state cookie
# ---------------------------------------------------------------------------


def test_google_login_redirects_to_google(client: TestClient) -> None:
    with (
        patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
        patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/auth/google/login",
            follow_redirects=False,
        )

    assert response.status_code == 302
    location = response.headers["location"]
    assert "accounts.google.com" in location
    assert "client_id=test-client-id" in location
    assert "response_type=code" in location
    assert "scope=" in location
    assert "state=" in location

    assert "oauth_state" in response.cookies


# ---------------------------------------------------------------------------
# 6.3 — Callback: valid code + new user → creates user, redirects with JWT
# ---------------------------------------------------------------------------


def test_google_callback_creates_new_user(client: TestClient, db: Session) -> None:
    email = random_email()
    state = "valid-state-creates-new"

    mock_cls = _make_httpx_mock(
        userinfo_data={
            "email": email,
            "name": "Brand New User",
            "email_verified": True,
        }
    )

    _set_state_cookie(client, state)
    try:
        with (
            patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
            patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
            patch("app.api.routes.google_auth.httpx.Client", mock_cls),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/auth/google/callback",
                params={"code": "auth-code-123", "state": state},
                follow_redirects=False,
            )
    finally:
        _clear_state_cookie(client)

    assert response.status_code == 302
    location = response.headers["location"]
    assert "access_token=" in location
    assert settings.FRONTEND_HOST in location

    user = db.exec(select(User).where(User.email == email)).first()
    assert user is not None
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.hashed_password is None
    assert user.full_name == "Brand New User"


# ---------------------------------------------------------------------------
# 6.4 — Callback: valid code + existing user → no new user, redirects with JWT
# ---------------------------------------------------------------------------


def test_google_callback_authenticates_existing_user(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    existing_user = User(email=email, is_active=True, hashed_password=None)
    db.add(existing_user)
    db.commit()
    db.refresh(existing_user)

    state = "valid-state-existing"
    mock_cls = _make_httpx_mock(
        userinfo_data={"email": email, "name": "Existing User", "email_verified": True}
    )

    before_count = len(db.exec(select(User)).all())

    _set_state_cookie(client, state)
    try:
        with (
            patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
            patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
            patch("app.api.routes.google_auth.httpx.Client", mock_cls),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/auth/google/callback",
                params={"code": "auth-code-456", "state": state},
                follow_redirects=False,
            )
    finally:
        _clear_state_cookie(client)

    assert response.status_code == 302
    assert "access_token=" in response.headers["location"]

    after_count = len(db.exec(select(User)).all())
    assert after_count == before_count


# ---------------------------------------------------------------------------
# 6.5 — Callback: state mismatch → HTTP 302, no DB write
# ---------------------------------------------------------------------------


def test_google_callback_state_mismatch(client: TestClient, db: Session) -> None:
    before_count = len(db.exec(select(User)).all())

    _set_state_cookie(client, "correct-state")
    try:
        with (
            patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
            patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/auth/google/callback",
                params={"code": "auth-code", "state": "wrong-state"},
                follow_redirects=False,
            )
    finally:
        _clear_state_cookie(client)

    assert response.status_code == 302
    location = response.headers["location"]
    assert settings.FRONTEND_HOST in location
    assert "error=state_mismatch" in location
    assert len(db.exec(select(User)).all()) == before_count


# ---------------------------------------------------------------------------
# 6.6 — Callback: missing oauth_state cookie → HTTP 302
# ---------------------------------------------------------------------------


def test_google_callback_missing_state_cookie(client: TestClient) -> None:
    _clear_state_cookie(client)

    with (
        patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
        patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/auth/google/callback",
            params={"code": "auth-code", "state": "some-state"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    location = response.headers["location"]
    assert settings.FRONTEND_HOST in location
    assert "error=missing_state" in location


# ---------------------------------------------------------------------------
# 6.7 — Callback: Google returns email_verified=False → HTTP 302, no user
# ---------------------------------------------------------------------------


def test_google_callback_unverified_email(client: TestClient, db: Session) -> None:
    state = "valid-state-unverified"
    mock_cls = _make_httpx_mock(
        userinfo_data={
            "email": random_email(),
            "name": "Unverified User",
            "email_verified": False,
        }
    )
    before_count = len(db.exec(select(User)).all())

    _set_state_cookie(client, state)
    try:
        with (
            patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
            patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
            patch("app.api.routes.google_auth.httpx.Client", mock_cls),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/auth/google/callback",
                params={"code": "auth-code", "state": state},
                follow_redirects=False,
            )
    finally:
        _clear_state_cookie(client)

    assert response.status_code == 302
    location = response.headers["location"]
    assert settings.FRONTEND_HOST in location
    assert "error=unverified_email" in location
    assert len(db.exec(select(User)).all()) == before_count


# ---------------------------------------------------------------------------
# W3 — Callback: Google token exchange fails (non-200) → HTTP 302, no user
# ---------------------------------------------------------------------------



def test_google_callback_token_exchange_failure(
    client: TestClient, db: Session
) -> None:
    state = "valid-state-token-fail"
    mock_cls = _make_httpx_mock(token_status=400)
    before_count = len(db.exec(select(User)).all())

    _set_state_cookie(client, state)
    try:
        with (
            patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
            patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
            patch("app.api.routes.google_auth.httpx.Client", mock_cls),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/auth/google/callback",
                params={"code": "expired-code", "state": state},
                follow_redirects=False,
            )
    finally:
        _clear_state_cookie(client)

    assert response.status_code == 302
    location = response.headers["location"]
    assert settings.FRONTEND_HOST in location
    assert "error=google_unreachable" in location
    assert len(db.exec(select(User)).all()) == before_count


# ---------------------------------------------------------------------------
# W4 — Callback: Google userinfo fetch fails (non-200) → HTTP 302, no user
# ---------------------------------------------------------------------------


def test_google_callback_userinfo_fetch_failure(
    client: TestClient, db: Session
) -> None:
    state = "valid-state-userinfo-fail"
    mock_cls = _make_httpx_mock(userinfo_status=400)
    before_count = len(db.exec(select(User)).all())

    _set_state_cookie(client, state)
    try:
        with (
            patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
            patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
            patch("app.api.routes.google_auth.httpx.Client", mock_cls),
        ):
            response = client.get(
                f"{settings.API_V1_STR}/auth/google/callback",
                params={"code": "auth-code", "state": state},
                follow_redirects=False,
            )
    finally:
        _clear_state_cookie(client)

    assert response.status_code == 302
    location = response.headers["location"]
    assert settings.FRONTEND_HOST in location
    assert "error=google_unreachable" in location
    assert len(db.exec(select(User)).all()) == before_count


# ---------------------------------------------------------------------------
# AC5 — Callback: Google returns ?error=access_denied → HTTP 302, no exchange
# ---------------------------------------------------------------------------


def test_google_callback_access_denied(client: TestClient) -> None:
    _clear_state_cookie(client)

    with (
        patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"),
        patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"),
    ):
        response = client.get(
            f"{settings.API_V1_STR}/auth/google/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    location = response.headers["location"]
    assert settings.FRONTEND_HOST in location
    assert "error=access_denied" in location


# ---------------------------------------------------------------------------
# 6.8 — POST /login/access-token for OAuth-only user → HTTP 400
# ---------------------------------------------------------------------------


def test_password_login_rejected_for_oauth_user(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    oauth_user = User(email=email, is_active=True, hashed_password=None)
    db.add(oauth_user)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": "any-password"},
    )

    assert response.status_code == 400
    assert "Google" in response.json()["detail"]
