"""Golden-set eval gate. `make eval` runs this; it exits 1 below threshold.

Retrieval always runs against `LocalRetriever` so the gate works offline. Generation
is optional: S1 may not have landed `TemplateGenerator` yet, in which case citation_ok
is skipped rather than failing the gate.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hrag.ports import Retriever

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"
K = 5
THRESHOLDS = {"hit_at_5": 0.8, "citation_ok": 1.0}


@dataclass
class EvalResult:
    hit_at_5: float
    citation_ok: float | None
    p50_ms: float
    p95_ms: float
    misses: list[str]


def load_golden(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, round(pct * (len(sorted_values) - 1)))
    return sorted_values[idx]


def evaluate(cases: list[dict[str, Any]], retriever: Retriever, generator: Any) -> EvalResult:
    hits = 0
    citation_checks: list[bool] = []
    latencies_ms: list[float] = []
    misses: list[str] = []

    for case in cases:
        start = time.perf_counter()
        passages = retriever.search(case["question"], K)
        latencies_ms.append((time.perf_counter() - start) * 1000)

        retrieved_ids = {p.id for p in passages}
        expected_ids = set(case["expect_any"])
        if retrieved_ids & expected_ids:
            hits += 1
        else:
            misses.append(case["question"])

        if generator is not None:
            answer = generator.generate(case["question"], passages)
            citation_checks.append(set(answer.citations) <= retrieved_ids)

    latencies_ms.sort()
    citation_ok = (sum(citation_checks) / len(citation_checks)) if citation_checks else None

    return EvalResult(
        hit_at_5=hits / len(cases) if cases else 0.0,
        citation_ok=citation_ok,
        p50_ms=_percentile(latencies_ms, 0.50),
        p95_ms=_percentile(latencies_ms, 0.95),
        misses=misses,
    )


def _load_generator() -> Any:
    try:
        from hrag.generator import TemplateGenerator
    except ImportError:
        return None
    return TemplateGenerator()


def _print_table(result: EvalResult) -> None:
    rows = [
        ("hit_at_5", f"{result.hit_at_5:.2f}", f">= {THRESHOLDS['hit_at_5']}"),
        (
            "citation_ok",
            f"{result.citation_ok:.2f}" if result.citation_ok is not None else "skipped",
            f">= {THRESHOLDS['citation_ok']}" if result.citation_ok is not None else "n/a",
        ),
        ("p50_latency_ms", f"{result.p50_ms:.1f}", "-"),
        ("p95_latency_ms", f"{result.p95_ms:.1f}", "-"),
    ]
    width = max(len(r[0]) for r in rows)
    print(f"{'metric':<{width}}  {'value':>8}  threshold")
    for name, value, threshold in rows:
        print(f"{name:<{width}}  {value:>8}  {threshold}")
    if result.misses:
        print(f"\nmissed {len(result.misses)} case(s):")
        for q in result.misses:
            print(f"  - {q}")


def main() -> int:
    cases = load_golden(GOLDEN_PATH)
    generator = _load_generator()
    if generator is None:
        print("hrag.generator.TemplateGenerator not importable yet, running retrieval-only "
              "(citation_ok skipped)")

    from hrag.retrieval.local import LocalRetriever

    result = evaluate(cases, LocalRetriever(), generator)
    _print_table(result)

    failed = result.hit_at_5 < THRESHOLDS["hit_at_5"]
    if result.citation_ok is not None and result.citation_ok < THRESHOLDS["citation_ok"]:
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
