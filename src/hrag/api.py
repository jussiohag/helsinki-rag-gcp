"""FastAPI request path: guard -> retrieve -> generate -> log, each stage
timed and returned. Adapter selection lives in config.py; `get_adapters` is a
FastAPI dependency so tests can override it with fakes.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hrag.config import Adapters, build_adapters
from hrag.ports import Passage, Turn

app = FastAPI(title="helsinki-rag")
_adapters = build_adapters()
_STATIC_DIR = Path(__file__).parent / "static"


def get_adapters() -> Adapters:
    return _adapters


class AskRequest(BaseModel):
    question: str
    channel: str = "web"
    language: str = "fi"


class PassageOut(BaseModel):
    id: str
    title: str
    text: str
    source_url: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[str]
    model: str
    no_answer: bool
    latency_ms: dict[str, int]
    passages: list[PassageOut]
    guard: str


def _passage_out(p: Passage) -> PassageOut:
    return PassageOut(id=p.id, title=p.title, text=p.text, source_url=p.source_url, score=p.score)


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, adapters: Adapters = Depends(get_adapters)) -> AskResponse:
    total_start = time.perf_counter()
    latency: dict[str, int] = {}
    turn_id = str(uuid.uuid4())
    question_hash = hashlib.sha256(req.question.encode("utf-8")).hexdigest()

    guard_start = time.perf_counter()
    guard_result = adapters.guard.check(req.question)
    latency["guard"] = _elapsed_ms(guard_start)

    if not guard_result.allowed:
        turn = Turn(
            turn_id=turn_id,
            channel=req.channel,
            language=req.language,
            question_hash=question_hash,
            model="",
            guard=guard_result.reason,
            outcome="blocked",
        )
        _write_turn(adapters, turn, latency, total_start)
        raise HTTPException(status_code=400, detail=guard_result.reason)

    retrieve_start = time.perf_counter()
    passages = adapters.retriever.search(req.question, k=5)
    latency["retrieve"] = _elapsed_ms(retrieve_start)

    generate_start = time.perf_counter()
    answer = adapters.generator.generate(req.question, passages)
    latency["generate"] = _elapsed_ms(generate_start)

    turn = Turn(
        turn_id=turn_id,
        channel=req.channel,
        language=req.language,
        question_hash=question_hash,
        passage_ids=[p.id for p in passages],
        cited_ids=list(answer.citations),
        model=answer.model,
        guard="ok",
        outcome="no_answer" if answer.no_answer else "answered",
    )
    _write_turn(adapters, turn, latency, total_start)

    return AskResponse(
        answer=answer.text,
        citations=list(answer.citations),
        model=answer.model,
        no_answer=answer.no_answer,
        latency_ms=latency,
        passages=[_passage_out(p) for p in passages],
        guard="ok",
    )


def _write_turn(adapters: Adapters, turn: Turn, latency: dict[str, int], total_start: float) -> None:
    """Stamps the turn with latencies known so far, then times the write itself."""
    turn.latency_ms = latency
    log_start = time.perf_counter()
    adapters.turnlog.write(turn)
    latency["log"] = _elapsed_ms(log_start)
    latency["total"] = _elapsed_ms(total_start)


@app.get("/healthz")
def healthz(adapters: Adapters = Depends(get_adapters)) -> dict[str, object]:
    return {"status": "ok", "adapters": adapters.names}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")
