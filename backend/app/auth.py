import hashlib
import time
from threading import Lock

from fastapi import Header, HTTPException, status

from app.config import settings
from app.database import supabase


class CurrentUser:
    def __init__(self, id: str, email: str | None):
        self.id = id
        self.email = email


# token-hash -> (expires_at_monotonic, CurrentUser). Keeps us from making a
# round-trip to Supabase Auth on every one of the many requests a page fires.
_cache: dict[str, tuple[float, CurrentUser]] = {}
_cache_lock = Lock()
_CACHE_MAX = 1024


def _key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _lookup_cached(token: str) -> CurrentUser | None:
    k = _key(token)
    with _cache_lock:
        hit = _cache.get(k)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        _cache.pop(k, None)
    return None


def _store(token: str, user: CurrentUser) -> None:
    if settings.AUTH_CACHE_TTL_SECONDS <= 0:
        return
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[_key(token)] = (time.monotonic() + settings.AUTH_CACHE_TTL_SECONDS, user)


def clear_auth_cache() -> None:
    with _cache_lock:
        _cache.clear()


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """
    Resolves the caller with Supabase Auth.

    The frontend signs in with supabase-js and sends its access token as
    'Authorization: Bearer <access_token>'. Instead of verifying the JWT
    signature ourselves (which breaks whenever a project changes its signing
    algorithm / moves to asymmetric keys), we ask Supabase Auth who the token
    belongs to. Supabase also rejects expired, revoked and signed-out tokens.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    cached = _lookup_cached(token)
    if cached:
        return cached

    try:
        response = supabase.auth.get_user(token)
        supa_user = response.user if response else None
    except Exception as exc:  # gotrue raises AuthApiError / AuthInvalidJwtError / network errors
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    if not supa_user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = CurrentUser(id=str(supa_user.id), email=supa_user.email)
    _store(token, user)
    return user


def get_optional_user(authorization: str | None = Header(default=None)) -> CurrentUser | None:
    """Same as get_current_user but returns None instead of raising (for public reads)."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None
