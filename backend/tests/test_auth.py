import time

import pytest
from fastapi import HTTPException

from app import auth as auth_module
from app.auth import get_current_user, get_optional_user
from app.config import settings
from tests.conftest import make_token


def test_valid_token_is_accepted(fake_db):
    user = get_current_user(authorization=f"Bearer {make_token('user-42', 'x@example.com')}")
    assert user.id == "user-42"
    assert user.email == "x@example.com"


def test_missing_header_rejected(fake_db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None)
    assert exc.value.status_code == 401
    assert fake_db.auth.calls == 0  # never bothers Supabase without a token


def test_malformed_header_rejected(fake_db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="NotBearer sometoken")
    assert exc.value.status_code == 401


def test_empty_bearer_rejected(fake_db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Bearer    ")
    assert exc.value.status_code == 401


def test_token_supabase_rejects_gives_401(fake_db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Bearer not-a-real-token")
    assert exc.value.status_code == 401
    assert "Invalid" in exc.value.detail


def test_token_signed_with_any_algorithm_is_fine_if_supabase_accepts_it(fake_db):
    # The old code hard-coded HS256 + the project JWT secret. Now the algorithm is
    # Supabase's problem, so asymmetric-key projects work: we only ask Supabase.
    assert get_current_user(authorization=f"Bearer {make_token('u-asym')}").id == "u-asym"


def test_supabase_returning_no_user_is_401(fake_db, monkeypatch):
    monkeypatch.setattr(fake_db.auth, "get_user", lambda jwt=None: None)
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=f"Bearer {make_token()}")
    assert exc.value.status_code == 401


def test_lookup_is_cached_between_requests(fake_db):
    hdr = f"Bearer {make_token('cached-user')}"
    get_current_user(authorization=hdr)
    get_current_user(authorization=hdr)
    get_current_user(authorization=hdr)
    assert fake_db.auth.calls == 1


def test_cache_expires(fake_db, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_CACHE_TTL_SECONDS", 1)
    hdr = f"Bearer {make_token('ttl-user')}"
    get_current_user(authorization=hdr)
    real = time.monotonic
    monkeypatch.setattr(auth_module.time, "monotonic", lambda: real() + 5)
    get_current_user(authorization=hdr)
    assert fake_db.auth.calls == 2


def test_revoked_token_rejected_after_cache_expires(fake_db, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_CACHE_TTL_SECONDS", 0)  # no caching
    tok = make_token("revoked-user")
    assert get_current_user(authorization=f"Bearer {tok}").id == "revoked-user"
    fake_db.auth.revoked.add(tok)
    with pytest.raises(HTTPException):
        get_current_user(authorization=f"Bearer {tok}")


def test_optional_user_returns_none_when_absent(fake_db):
    assert get_optional_user(authorization=None) is None


def test_optional_user_returns_none_for_bad_token(fake_db):
    assert get_optional_user(authorization="Bearer garbage") is None


def test_optional_user_returns_user_when_present(fake_db):
    user = get_optional_user(authorization=f"Bearer {make_token('user-7')}")
    assert user.id == "user-7"


def test_endpoint_401_for_bad_token(app_client):
    resp = app_client.post("/api/documents", json={"title": "x"}, headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401
