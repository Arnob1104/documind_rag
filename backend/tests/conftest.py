import os
import sys
import types
import uuid
import re
from datetime import datetime, timezone

import pytest

# ── Env vars must exist before app.config is imported anywhere ──────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test.service.key")  # JWT-shaped: supabase-py rejects other formats at import
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")

# ── Stub sentence_transformers so tests don't need torch / network access to
#    huggingface.co (blocked in this sandbox anyway). Produces deterministic,
#    content-derived fake vectors so similarity search is still meaningful. ──
_fake_st = types.ModuleType("sentence_transformers")


class _FakeSentenceTransformer:
    def __init__(self, *a, **k):
        pass

    def encode(self, texts, normalize_embeddings=True):
        import hashlib
        import numpy as np
        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            vec = [b / 255.0 for b in h][:384]
            vec += [0.0] * (384 - len(vec))
            vecs.append(vec)
        return np.array(vecs)  # real SentenceTransformer.encode() returns an ndarray, so keep parity (.tolist())


_fake_st.SentenceTransformer = _FakeSentenceTransformer
sys.modules["sentence_transformers"] = _fake_st


# ── Minimal in-memory fake of the supabase-py fluent query builder ──────────
class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.op = None
        self.payload = None
        self.filters = []  # list of (col, op, val)
        self._order = None
        self._limit = None
        self._single = False

    # filtering
    def eq(self, col, val):
        self.filters.append((col, "eq", val))
        return self

    def ilike(self, col, pattern):
        self.filters.append((col, "ilike", pattern))
        return self

    def or_(self, expr):
        # expr like "is_public.eq.true,author_id.eq.<id>"
        self.filters.append(("__or__", "or", expr))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        # Mirrors real postgrest-py: .single() *raises* if the row count isn't
        # exactly 1 (it does not just return None). Code that wants graceful
        # "not found" behavior must use .maybe_single() instead.
        self._single = "strict"
        return self

    def maybe_single(self):
        self._single = "maybe"
        return self

    # mutations
    def select(self, *_a, **_k):
        self.op = self.op or "select"
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.op = "update"
        self.payload = payload
        return self

    def upsert(self, payload):
        self.op = "upsert"
        self.payload = payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _row_matches(self, row):
        for col, op, val in self.filters:
            if col == "__or__":
                clauses = val.split(",")
                if not any(self._match_clause(row, c) for c in clauses):
                    return False
            elif op == "eq":
                if row.get(col) != val:
                    return False
            elif op == "ilike":
                pattern = val.strip("%").lower()
                if pattern not in str(row.get(col, "")).lower():
                    return False
        return True

    @staticmethod
    def _match_clause(row, clause):
        col, op, val = clause.split(".", 2)
        if val == "true":
            val = True
        elif val == "false":
            val = False
        return row.get(col) == val

    def execute(self):
        table = self.db.setdefault(self.table_name, [])

        if self.op == "insert":
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for r in rows:
                row = dict(r)
                row.setdefault("id", str(uuid.uuid4()))
                now = datetime.now(timezone.utc).isoformat()
                row.setdefault("created_at", now)
                row.setdefault("updated_at", now)
                table.append(row)
                out.append(row)
            return Result(out)

        if self.op == "upsert":
            rows = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for r in rows:
                # naive upsert: match on all keys given except non-key-ish; here
                # our schema only upserts document_tags on (document_id, tag_id)
                match = [
                    row for row in table
                    if all(row.get(k) == v for k, v in r.items() if k in ("document_id", "tag_id"))
                ]
                if match:
                    match[0].update(r)
                    out.append(match[0])
                else:
                    row = dict(r)
                    row.setdefault("id", str(uuid.uuid4()))
                    table.append(row)
                    out.append(row)
            return Result(out)

        if self.op == "update":
            matched = [r for r in table if self._row_matches(r)]
            for r in matched:
                r.update(self.payload)
                r["updated_at"] = datetime.now(timezone.utc).isoformat()
            return Result(matched)

        if self.op == "delete":
            matched = [r for r in table if self._row_matches(r)]
            for r in matched:
                table.remove(r)
            return Result(matched)

        # select
        rows = [r for r in table if self._row_matches(r)]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: r.get(col) or "", reverse=desc)
        if self._limit:
            rows = rows[: self._limit]
        if self._single == "strict":
            if len(rows) != 1:
                raise Exception(
                    f"PGRST116-like error: .single() expected exactly 1 row on "
                    f"'{self.table_name}', got {len(rows)}. Use .maybe_single() "
                    f"if zero rows is an expected, handled case."
                )
            return Result(rows[0])
        if self._single == "maybe":
            return Result(rows[0] if rows else None)
        return Result(rows)


class FakeRPC:
    def __init__(self, db, fn_name, params):
        self.db = db
        self.fn_name = fn_name
        self.params = params

    def execute(self):
        if self.fn_name != "match_document_chunks":
            return Result([])
        query_embedding = self.params["query_embedding"]
        user_id = self.params["requesting_user_id"]
        top_k = self.params["match_count"]

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(y * y for y in b) ** 0.5
            return dot / (na * nb) if na and nb else 0.0

        docs = {d["id"]: d for d in self.db.get("documents", [])}
        visible_chunks = [
            c for c in self.db.get("document_chunks", [])
            if c["document_id"] in docs
            and (docs[c["document_id"]]["is_public"] or docs[c["document_id"]]["author_id"] == user_id)
        ]
        scored = [
            {
                "chunk_id": c["id"],
                "document_id": c["document_id"],
                "content": c["content"],
                "similarity": cosine(c["embedding"], query_embedding),
                "title": docs[c["document_id"]]["title"],
            }
            for c in visible_chunks
        ]
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return Result(scored[:top_k])


class _FakeUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email


class _FakeUserResponse:
    def __init__(self, user):
        self.user = user


class FakeAuth:
    """
    Stands in for supabase.auth. Tokens are minted by make_token() as
    'test-token|<user_id>|<email>'; anything else is rejected the way GoTrue
    rejects a bad/expired JWT (by raising).
    """

    def __init__(self):
        self.calls = 0
        self.revoked = set()

    def get_user(self, jwt=None):
        self.calls += 1
        if not jwt or not jwt.startswith("test-token|") or jwt in self.revoked:
            raise Exception("invalid JWT: unable to parse or verify signature")
        _, user_id, email = jwt.split("|", 2)
        return _FakeUserResponse(_FakeUser(user_id, email))


class FakeSupabaseClient:
    def __init__(self):
        self.db = {}
        self.auth = FakeAuth()

    def table(self, name):
        return FakeQuery(self.db, name)

    def rpc(self, fn_name, params):
        return FakeRPC(self.db, fn_name, params)


@pytest.fixture
def fake_db(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr("app.database.supabase", client)
    monkeypatch.setattr("app.routers.documents.supabase", client)
    monkeypatch.setattr("app.routers.tags.supabase", client)
    monkeypatch.setattr("app.routers.upload.supabase", client)
    monkeypatch.setattr("app.routers.search.supabase", client)
    monkeypatch.setattr("app.routers.chat.supabase", client)
    monkeypatch.setattr("app.services.rag.supabase", client)
    monkeypatch.setattr("app.services.agent_tools.supabase", client)
    monkeypatch.setattr("app.auth.supabase", client)
    from app.auth import clear_auth_cache
    clear_auth_cache()
    return client


@pytest.fixture
def app_client(fake_db):
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


def make_token(user_id="user-1", email="alice@example.com"):
    return f"test-token|{user_id}|{email}"


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token('user-1', 'alice@example.com')}"}


@pytest.fixture
def other_auth_headers():
    return {"Authorization": f"Bearer {make_token('user-2', 'bob@example.com')}"}
