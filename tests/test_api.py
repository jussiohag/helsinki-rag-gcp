import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hrag.config import Adapters
from hrag.generator import TemplateGenerator
from hrag.guard import HeuristicGuard
from hrag.ports import Passage
from hrag.retrieval.local import LocalRetriever
from hrag.turnlog import JsonlTurnLog


class RecordingRetriever:
    def __init__(self, passages: list[Passage]) -> None:
        self.passages = passages

    def search(self, query: str, k: int) -> list[Passage]:
        return self.passages[:k]


@pytest.fixture
def turnlog_path(tmp_path: Path) -> Path:
    return tmp_path / "turns.jsonl"


@pytest.fixture
def client(turnlog_path: Path):
    import hrag.api as api_module

    passages = [
        Passage(id="1", title="Kannel Library", text="Kannelpolku 6. Phone 09-123.", source_url="", score=3),
    ]
    adapters = Adapters(
        retriever=RecordingRetriever(passages),
        generator=TemplateGenerator(),
        guard=HeuristicGuard(),
        turnlog=JsonlTurnLog(path=turnlog_path),
        names={"retriever": "fake", "generator": "template", "guard": "heuristic", "turnlog": "jsonl"},
    )
    api_module.app.dependency_overrides[api_module.get_adapters] = lambda: adapters
    yield TestClient(api_module.app)
    api_module.app.dependency_overrides.clear()


def _read_turns(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_ask_happy_path(client: TestClient, turnlog_path: Path):
    response = client.post("/ask", json={"question": "Where is Kannel library?"})
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "template"
    assert body["no_answer"] is False
    assert body["citations"] == ["1"]
    assert "Kannel Library" in body["answer"]
    assert body["guard"] == "ok"
    assert len(body["passages"]) == 1
    assert body["passages"][0]["id"] == "1"
    assert body["passages"][0]["title"] == "Kannel Library"
    assert body["passages"][0]["source_url"] == ""
    assert body["passages"][0]["score"] == 3
    for stage in ("guard", "retrieve", "generate", "log", "total"):
        assert stage in body["latency_ms"]
        assert isinstance(body["latency_ms"][stage], int)

    turns = _read_turns(turnlog_path)
    assert len(turns) == 1
    assert turns[0]["outcome"] == "answered"
    assert turns[0]["question_hash"] == hashlib.sha256(b"Where is Kannel library?").hexdigest()
    assert "question" not in turns[0]


def test_ask_no_answer_when_no_passages_found(turnlog_path: Path):
    import hrag.api as api_module

    adapters = Adapters(
        retriever=RecordingRetriever([]),
        generator=TemplateGenerator(),
        guard=HeuristicGuard(),
        turnlog=JsonlTurnLog(path=turnlog_path),
        names={"retriever": "fake", "generator": "template", "guard": "heuristic", "turnlog": "jsonl"},
    )
    api_module.app.dependency_overrides[api_module.get_adapters] = lambda: adapters
    try:
        client = TestClient(api_module.app)
        response = client.post("/ask", json={"question": "asdf qwerty zzz"})
    finally:
        api_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["no_answer"] is True
    assert body["passages"] == []
    assert body["guard"] == "ok"

    turns = _read_turns(turnlog_path)
    assert turns[0]["outcome"] == "no_answer"


def test_ask_blocked_input_returns_400_and_logs_blocked_turn(client: TestClient, turnlog_path: Path):
    long_question = "a" * 2001
    response = client.post("/ask", json={"question": long_question})

    assert response.status_code == 400
    assert "2000" in response.json()["detail"]

    turns = _read_turns(turnlog_path)
    assert len(turns) == 1
    assert turns[0]["outcome"] == "blocked"
    assert "question" not in turns[0]
    assert turns[0]["question_hash"] == hashlib.sha256(long_question.encode("utf-8")).hexdigest()


def test_healthz_reports_adapter_names(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["adapters"]["retriever"] == "fake"


def test_default_app_uses_local_adapters():
    import hrag.api as api_module

    assert isinstance(api_module.get_adapters().retriever, LocalRetriever)
