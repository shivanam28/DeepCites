import logging
from dataclasses import dataclass, field

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)
UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None
    token: str = field(default="", repr=False)  # repr=False keeps it out of logs


def verify_token(token: str) -> AuthUser:
    """Ask the Supabase Auth server who this token belongs to."""
    s = get_settings()
    try:
        r = httpx.get(
            f"{s.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": s.supabase_publishable_key, "Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("Auth server unreachable: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    if 400 <= r.status_code < 500:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers=UNAUTHORIZED)
    if r.status_code != 200:
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    try:
        data = r.json()
        user_id = data["id"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers=UNAUTHORIZED)
    return AuthUser(id=str(user_id), email=data.get("email"), token=token)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthUser:
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing bearer token", headers=UNAUTHORIZED)
    return verify_token(creds.credentials)