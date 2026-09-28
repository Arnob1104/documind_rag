import json
import types

import groq
import httpx

from app.services import agent as agent_module
from app.services import agent_tools
from app.services.rag import index_document


# ── Fake Groq: routes each call to a per-agent script ────────────────────────
class _FnCall:
    def __init__(self, name, arguments, call_id=None):
        self.id = call_id or f"call_{name}"
        args = arguments if isinstance(arguments, str) else json.dumps(arguments)
        self.function = types.SimpleNamespace(name=name, arguments=args)


def tool_call(name, arguments):
    return types.SimpleNamespace(content=None, tool_calls=[_FnCall(name, arguments)])


def say(text):
    return types.SimpleNamespace(content=text, tool_calls=None)


def route(next_):
    return say(json.dumps({"next": next_}))


def _identify(messages):
    system = messages[0]["content"]
    if "supervisor" in system:
        return "supervisor"
    if "Retriever agent" in system:
        return "retriever"
    if "Tagger agent" in system:
        return "tagger"
    return "responder"


class FakeGroq:
    """scripts: {'supervisor': [...], 'retriever': [...], 'tagger': [...], 'responder': [...]}"""

    def __init__(self, **scripts):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.calls = []  # (agent, messages, kwargs)

        class _Completions:
            def create(inner, **kwargs):
                agent = _identify(kwargs["messages"])
                self.calls.append((agent, kwargs["messages"], kwargs))
                queue = self.scripts.get(agent)
                if not queue:
                    raise AssertionError(f"unexpected extra LLM call from '{agent}' agent")
                item = queue.pop(0)
                if isinstance(item, Exception):
                    raise item
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=item)])

        self.chat = types.SimpleNamespace(completions=_Completions())

    def agents_called(self):
        return [a for a, _, _ in self.calls]


def use(monkeypatch, fake):
    monkeypatch.setattr(agent_module, "client", fake)
    return fake


def _doc(fake_db, id, title, author="user-1", public=False, content=""):
    return fake_db.table("documents").insert(
        {"id": id, "title": title, "content": content, "is_public": public, "author_id": author}
    ).execute().data[0]


def _api_error():
    return groq.APIConnectionError(request=httpx.Request("POST", "http://groq.test"))


# ── Graph behaviour ──────────────────────────────────────────────────────────
def test_small_talk_goes_supervisor_then_responder_only(monkeypatch, fake_db):
    fake = use(monkeypatch, FakeGroq(supervisor=[route("respond")], responder=[say("Hi! I can search and tag your docs.")]))
    result = agent_module.run_agent("user-1", "hello")
    assert result["reply"] == "Hi! I can search and tag your docs."
    assert result["agents_used"] == []
    assert result["actions_taken"] == []
    assert fake.agents_called() == ["supervisor", "responder"]


def test_retriever_answers_questions_and_returns_sources(monkeypatch, fake_db):
    _doc(fake_db, "doc-1", "Rockets", public=True)
    index_document("doc-1", "Rocket engines produce thrust through combustion of propellant.")
    fake = use(
        monkeypatch,
        FakeGroq(
            supervisor=[route("retriever"), route("respond")],
            retriever=[tool_call("search_knowledge_base", {"query": "how do rockets work"}), say("Rockets expel propellant to make thrust (from *Rockets*).")],
        ),
    )
    result = agent_module.run_agent("user-1", "how do rockets work?")
    assert "thrust" in result["reply"]
    assert result["agents_used"] == ["retriever"]
    assert result["actions_taken"] == ["search_knowledge_base"]
    assert len(result["sources"]) >= 1 and result["sources"][0]["document_id"] == "doc-1"
    assert "responder" not in fake.agents_called()  # single specialist answer is passed through


def test_tagger_writes_tags_owned_by_the_user(monkeypatch, fake_db):
    _doc(fake_db, "doc-2", "Quarterly Report")
    use(
        monkeypatch,
        FakeGroq(
            supervisor=[route("tagger"), route("respond")],
            tagger=[tool_call("apply_tags", {"document_id": "doc-2", "tags": ["Finance", "q3"]}), say("Tagged *Quarterly Report* with finance and q3.")],
        ),
    )
    result = agent_module.run_agent("user-1", "tag my quarterly report as finance and q3")
    assert result["agents_used"] == ["tagger"]
    assert "apply_tags" in result["actions_taken"]

    tags = {t["name"]: t for t in fake_db.db["tags"]}
    assert set(tags) == {"finance", "q3"}
    assert all(t["created_by"] == "user-1" for t in tags.values())
    assert len([dt for dt in fake_db.db["document_tags"] if dt["document_id"] == "doc-2"]) == 2


def test_both_agents_run_in_order_and_responder_merges(monkeypatch, fake_db):
    _doc(fake_db, "doc-3", "Launch plan", content="Launch is in March.")
    fake = use(
        monkeypatch,
        FakeGroq(
            supervisor=[route("retriever"), route("tagger"), route("respond")],
            retriever=[say("Summary: the launch is planned for March (Launch plan).")],
            tagger=[tool_call("apply_tags", {"document_id": "doc-3", "tags": ["launch"]}), say("Applied tag 'launch' to Launch plan.")],
            responder=[say("Summary: launch is in March. I also tagged it `launch`.")],
        ),
    )
    result = agent_module.run_agent("user-1", "summarize my launch plan and tag it")
    assert result["agents_used"] == ["retriever", "tagger"]
    # supervisor -> retriever -> supervisor -> tagger (tool call + final answer) -> responder.
    # After both specialists have run the supervisor routes without spending an LLM call.
    assert fake.agents_called() == ["supervisor", "retriever", "supervisor", "tagger", "tagger", "responder"]
    assert "tagged" in result["reply"]

    # the tagger was shown the retriever's findings
    tagger_msgs = next(m for a, m, _ in fake.calls if a == "tagger")
    assert any("Summary: the launch is planned for March" in str(m["content"]) for m in tagger_msgs)
    # and the responder saw both agents' notes
    responder_msgs = next(m for a, m, _ in fake.calls if a == "responder")
    assert "[retriever agent]" in responder_msgs[-1]["content"] and "[tagger agent]" in responder_msgs[-1]["content"]


def test_each_specialist_runs_at_most_once(monkeypatch, fake_db):
    fake = use(
        monkeypatch,
        FakeGroq(
            supervisor=[route("retriever"), route("retriever")],  # tries to send it back to retriever
            retriever=[say("Found nothing relevant.")],
        ),
    )
    result = agent_module.run_agent("user-1", "find stuff")
    assert result["agents_used"] == ["retriever"]
    assert fake.agents_called().count("retriever") == 1


def test_unparseable_routing_falls_back_to_read_only_retriever(monkeypatch, fake_db):
    fake = use(
        monkeypatch,
        FakeGroq(supervisor=[say("I think the retriever should go, obviously"), say("¯\\_(ツ)_/¯")], retriever=[say("Here you go.")]),
    )
    result = agent_module.run_agent("user-1", "what do my notes say?")
    assert result["agents_used"] == ["retriever"]  # never defaults to the writing agent
    assert result["reply"] == "Here you go."


def test_invalid_route_value_is_rejected(monkeypatch, fake_db):
    use(monkeypatch, FakeGroq(supervisor=[route("admin"), route("respond")], retriever=[say("ok")]))
    result = agent_module.run_agent("user-1", "hi")
    assert result["agents_used"] == ["retriever"]


def test_supervisor_api_failure_falls_back(monkeypatch, fake_db):
    use(monkeypatch, FakeGroq(supervisor=[_api_error(), _api_error()], retriever=[say("Recovered.")]))
    result = agent_module.run_agent("user-1", "search please")
    assert result["reply"] == "Recovered."


def test_worker_model_failure_returns_friendly_message_not_exception(monkeypatch, fake_db):
    use(monkeypatch, FakeGroq(supervisor=[route("retriever"), route("respond")], retriever=[_api_error()]))
    result = agent_module.run_agent("user-1", "search please")
    assert "problem talking to the language model" in result["reply"]


def test_worker_stops_after_max_steps(monkeypatch, fake_db):
    use(
        monkeypatch,
        FakeGroq(supervisor=[route("retriever"), route("respond")], retriever=[tool_call("list_documents", {})] * 10),
    )
    result = agent_module.run_agent("user-1", "keep going forever", max_steps=3)
    assert "ran out of steps" in result["reply"]
    assert result["actions_taken"] == ["list_documents"] * 3


def test_history_is_passed_to_the_specialist(monkeypatch, fake_db):
    fake = use(monkeypatch, FakeGroq(supervisor=[route("retriever"), route("respond")], retriever=[say("ok")]))
    history = [{"role": "user", "content": "I'm reading the Apollo doc"}, {"role": "assistant", "content": "Got it."}]
    agent_module.run_agent("user-1", "summarize it", history=history)
    msgs = next(m for a, m, _ in fake.calls if a == "retriever")
    assert {"role": "user", "content": "I'm reading the Apollo doc"} in msgs


def test_tool_call_messages_are_plain_dicts(monkeypatch, fake_db):
    fake = use(
        monkeypatch,
        FakeGroq(supervisor=[route("retriever"), route("respond")], retriever=[tool_call("list_documents", {}), say("done")]),
    )
    agent_module.run_agent("user-1", "list")
    second_call_msgs = [m for a, m, _ in fake.calls if a == "retriever"][1]
    assistant = next(m for m in second_call_msgs if m["role"] == "assistant")
    assert isinstance(assistant["tool_calls"][0], dict)
    assert assistant["tool_calls"][0]["function"]["name"] == "list_documents"


def test_each_agent_is_only_offered_its_own_tools(monkeypatch, fake_db):
    fake = use(
        monkeypatch,
        FakeGroq(supervisor=[route("retriever"), route("tagger"), route("respond")], retriever=[say("r")], tagger=[say("t")], responder=[say("x")]),
    )
    agent_module.run_agent("user-1", "do both")
    offered = {a: {t["function"]["name"] for t in kw["tools"]} for a, _, kw in fake.calls if "tools" in kw}
    assert offered["retriever"] == {"search_knowledge_base", "list_documents", "get_document"}
    assert offered["tagger"] == {"list_my_documents", "list_tags", "get_document", "apply_tags"}
    assert "apply_tags" not in offered["retriever"]  # the read-only agent can't write


def test_graph_has_expected_topology():
    nodes = set(agent_module.GRAPH.get_graph().nodes)
    assert {"supervisor", "retriever", "tagger", "responder"} <= nodes


# ── Tool safety ──────────────────────────────────────────────────────────────
def test_retriever_cannot_call_write_tools_even_if_model_tries(monkeypatch, fake_db):
    _doc(fake_db, "doc-4", "Mine")
    use(
        monkeypatch,
        FakeGroq(
            supervisor=[route("retriever"), route("respond")],
            retriever=[tool_call("apply_tags", {"document_id": "doc-4", "tags": ["pwned"]}), say("done")],
        ),
    )
    agent_module.run_agent("user-1", "please tag")
    assert fake_db.db.get("tags", []) == []
    assert fake_db.db.get("document_tags", []) == []


def test_apply_tags_rejects_non_owner(fake_db):
    _doc(fake_db, "doc-5", "Not yours", author="someone-else", public=True)
    out = agent_tools.execute_tool("apply_tags", json.dumps({"document_id": "doc-5", "tags": ["x"]}), "user-1", agent_tools.TAGGER_TOOLS)
    assert "error" in out
    assert fake_db.db.get("document_tags", []) == []


def test_apply_tags_reuses_existing_tag_and_keeps_its_owner(fake_db):
    fake_db.table("tags").insert({"id": "t1", "name": "finance", "created_by": "someone-else"}).execute()
    _doc(fake_db, "doc-6", "Mine")
    out = agent_tools.execute_tool("apply_tags", json.dumps({"document_id": "doc-6", "tags": ["FINANCE", " finance "]}), "user-1", agent_tools.TAGGER_TOOLS)
    assert out == {"applied_tags": ["finance"]}
    assert len(fake_db.db["tags"]) == 1 and fake_db.db["tags"][0]["created_by"] == "someone-else"


def test_apply_tags_limits_count_and_length(fake_db):
    _doc(fake_db, "doc-7", "Mine")
    tags = [f"tag{i}" for i in range(20)] + ["x" * 200]
    out = agent_tools.execute_tool("apply_tags", json.dumps({"document_id": "doc-7", "tags": tags}), "user-1", agent_tools.TAGGER_TOOLS)
    assert len(out["applied_tags"]) == agent_tools.MAX_TAGS_PER_CALL


def test_model_supplied_user_id_is_ignored(fake_db):
    _doc(fake_db, "secret", "Victim's diary", author="victim", public=False)
    index_document("secret", "victim private password hunter2")
    out = agent_tools.execute_tool(
        "search_knowledge_base",
        json.dumps({"query": "password", "user_id": "victim"}),
        "attacker",
        agent_tools.RETRIEVER_TOOLS,
    )
    assert out["results"] == []
    doc = agent_tools.execute_tool("get_document", json.dumps({"document_id": "secret", "user_id": "victim"}), "attacker", agent_tools.RETRIEVER_TOOLS)
    assert "error" in doc


def test_get_document_includes_pdf_text_but_not_twice(fake_db):
    d = _doc(fake_db, "doc-8", "With PDF", content="body")
    d["pdf_data"] = [{"extracted_text": "pdf words here"}]
    out = agent_tools.execute_tool("get_document", json.dumps({"document_id": "doc-8"}), "user-1", agent_tools.RETRIEVER_TOOLS)
    assert out["document"]["content"].count("pdf words here") == 1
    d["content"] = "body\n\npdf words here"
    out = agent_tools.execute_tool("get_document", json.dumps({"document_id": "doc-8"}), "user-1", agent_tools.RETRIEVER_TOOLS)
    assert out["document"]["content"].count("pdf words here") == 1


def test_bad_tool_arguments_and_unknown_tools_return_errors_not_exceptions(fake_db):
    allowed = agent_tools.RETRIEVER_TOOLS
    assert "error" in agent_tools.execute_tool("get_document", "{not json", "user-1", allowed)
    assert "error" in agent_tools.execute_tool("get_document", "[1,2]", "user-1", allowed)
    assert "error" in agent_tools.execute_tool("drop_database", "{}", "user-1", allowed)
    assert "error" in agent_tools.execute_tool("search_knowledge_base", "{}", "user-1", allowed)


def test_tool_result_is_truncated(fake_db):
    assert len(agent_tools.dump_result({"x": "a" * 20000})) < agent_tools.MAX_TOOL_RESULT_CHARS + 50


# ── Chat endpoint ────────────────────────────────────────────────────────────
def test_chat_endpoint_persists_session_messages_and_reports_agents(app_client, auth_headers, monkeypatch, fake_db):
    use(monkeypatch, FakeGroq(supervisor=[route("retriever"), route("respond")], retriever=[say("Sure, here's a summary.")]))
    resp = app_client.post("/api/chat", json={"message": "summarize my notes"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Sure, here's a summary."
    assert body["agents_used"] == ["retriever"]
    session_id = body["session_id"]

    sessions = app_client.get("/api/chat/sessions", headers=auth_headers).json()
    assert any(s["id"] == session_id for s in sessions)
    messages = app_client.get(f"/api/chat/sessions/{session_id}/messages", headers=auth_headers).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_chat_second_turn_receives_history(app_client, auth_headers, monkeypatch, fake_db):
    fake = use(
        monkeypatch,
        FakeGroq(supervisor=[route("retriever"), route("respond")] * 2, retriever=[say("first answer"), say("second answer")]),
    )
    first = app_client.post("/api/chat", json={"message": "first question"}, headers=auth_headers).json()
    app_client.post("/api/chat", json={"message": "and then?", "session_id": first["session_id"]}, headers=auth_headers)
    second_call = [m for a, m, _ in fake.calls if a == "retriever"][1]
    contents = [m["content"] for m in second_call]
    assert "first question" in contents and "first answer" in contents


def test_chat_endpoint_rejects_others_session(app_client, auth_headers, other_auth_headers, monkeypatch, fake_db):
    use(monkeypatch, FakeGroq(supervisor=[route("respond")], responder=[say("ok")]))
    first = app_client.post("/api/chat", json={"message": "hi"}, headers=auth_headers).json()
    stolen = app_client.post("/api/chat", json={"message": "hi again", "session_id": first["session_id"]}, headers=other_auth_headers)
    assert stolen.status_code == 403
    assert app_client.get(f"/api/chat/sessions/{first['session_id']}/messages", headers=other_auth_headers).status_code == 403


def test_chat_requires_auth(app_client):
    assert app_client.post("/api/chat", json={"message": "hi"}).status_code == 401
