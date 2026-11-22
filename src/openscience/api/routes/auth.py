"""Authentication routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status

from openscience.api.config import get_settings
from openscience.api.models.user import get_user, verify_password
from openscience.api.schemas.request import LoginRequest
from openscience.api.schemas.response import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(username: str) -> str:
    """Issue a signed bearer token.

    Uses ``jwt`` (PyJWT) when available; otherwise falls back to an
    unsigned, base64-url-encoded token suitable only for development.
    """
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    claims = {"sub": username, "exp": expires}

    try:
        import jwt  # type: ignore

        return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)
    except ImportError:
        # Development fallback: NOT cryptographically secure.
        import base64
        import json

        payload = json.dumps(
            {"sub": username, "exp": expires.isoformat()}
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii")


@router.post("/token", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """Exchange username/password for an access token."""
    user = get_user(payload.username)
    if user is None or not user.is_active():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    settings = get_settings()
    token = _issue_token(user.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
