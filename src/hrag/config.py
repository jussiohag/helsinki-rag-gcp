"""Adapter selection from environment variables. Local adapters are the
default and need no network; naming an adapter kind in the matching env var
switches to its cloud counterpart. See AGENTS.md for the variable names.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from hrag.generator import GeminiGenerator, TemplateGenerator
from hrag.guard import HeuristicGuard, ModelArmorGuard
from hrag.ports import Generator, Guard, Retriever, TurnLog
from hrag.retrieval.local import LocalRetriever
from hrag.retrieval.vertex import VertexSearchRetriever
from hrag.turnlog import BigQueryTurnLog, JsonlTurnLog


@dataclass(frozen=True)
class Adapters:
    retriever: Retriever
    generator: Generator
    guard: Guard
    turnlog: TurnLog
    names: dict[str, str]


def build_adapters() -> Adapters:
    retriever_kind = os.environ.get("HRAG_RETRIEVER", "local")
    generator_kind = os.environ.get("HRAG_GENERATOR", "template")
    guard_kind = os.environ.get("HRAG_GUARD", "heuristic")
    turnlog_kind = os.environ.get("HRAG_TURNLOG", "jsonl")

    retriever: Retriever = VertexSearchRetriever() if retriever_kind == "vertex" else LocalRetriever()
    generator: Generator = GeminiGenerator() if generator_kind == "gemini" else TemplateGenerator()
    guard: Guard = ModelArmorGuard() if guard_kind == "model_armor" else HeuristicGuard()
    turnlog: TurnLog = BigQueryTurnLog() if turnlog_kind == "bigquery" else JsonlTurnLog()

    return Adapters(
        retriever=retriever,
        generator=generator,
        guard=guard,
        turnlog=turnlog,
        names={
            "retriever": retriever_kind,
            "generator": generator_kind,
            "guard": guard_kind,
            "turnlog": turnlog_kind,
        },
    )
