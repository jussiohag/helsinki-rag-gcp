"""Interfaces between components. Local implementations run with no network; GCP ones are env-gated."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Passage:
    id: str
    title: str
    text: str
    source_url: str
    score: float = 0.0


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[str, ...]
    model: str
    no_answer: bool = False


@dataclass
class Turn:
    """One request, logged without the raw question text. Stage latencies in milliseconds."""

    turn_id: str
    channel: str
    language: str
    question_hash: str
    passage_ids: list[str] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    model: str = ""
    guard: str = "ok"
    latency_ms: dict[str, int] = field(default_factory=dict)
    outcome: str = "answered"


class Retriever(Protocol):
    def search(self, query: str, k: int) -> list[Passage]: ...


class Generator(Protocol):
    def generate(self, question: str, passages: list[Passage]) -> Answer: ...


class Guard(Protocol):
    def check(self, text: str) -> GuardResult: ...


class TurnLog(Protocol):
    def write(self, turn: Turn) -> None: ...
