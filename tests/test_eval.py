import csv
import json
from pathlib import Path

from eval.run import GOLDEN_PATH, THRESHOLDS, evaluate, load_golden
from hrag.retrieval.local import LocalRetriever

DATA = Path(__file__).resolve().parents[1] / "data" / "helsinki_service_points.csv"


def test_golden_ids_exist_in_csv():
    """Every expect_any id in the golden set must be a real row id, not a typo."""
    with DATA.open(encoding="utf-8") as f:
        known_ids = {row["id"] for row in csv.DictReader(f)}
    for case in load_golden(GOLDEN_PATH):
        for expected_id in case["expect_any"]:
            assert expected_id in known_ids, f"{expected_id} missing from CSV ({case['question']!r})"


def test_golden_has_thirty_cases_with_required_fields():
    cases = load_golden(GOLDEN_PATH)
    assert len(cases) == 30
    for case in cases:
        assert case["question"]
        assert case["expect_any"]
        assert case["language"] in {"fi", "en"}


def test_golden_is_mixed_language():
    cases = load_golden(GOLDEN_PATH)
    languages = {case["language"] for case in cases}
    assert languages == {"fi", "en"}


def test_evaluate_hits_threshold_with_local_retriever():
    cases = load_golden(GOLDEN_PATH)
    result = evaluate(cases, LocalRetriever(), generator=None)
    assert result.hit_at_5 >= THRESHOLDS["hit_at_5"]
    assert result.citation_ok is None  # no generator supplied
    assert result.p50_ms >= 0
    assert result.p95_ms >= result.p50_ms


def test_evaluate_reports_per_case_misses():
    cases = [{"question": "zzz-not-in-corpus-nonsense", "expect_any": ["999999999"], "language": "en"}]
    result = evaluate(cases, LocalRetriever(), generator=None)
    assert result.hit_at_5 == 0.0
    assert result.misses == ["zzz-not-in-corpus-nonsense"]


def test_load_golden_parses_jsonl(tmp_path):
    p = tmp_path / "mini.jsonl"
    p.write_text(
        json.dumps({"question": "q", "expect_any": ["1"], "language": "en"}) + "\n",
        encoding="utf-8",
    )
    cases = load_golden(p)
    assert cases == [{"question": "q", "expect_any": ["1"], "language": "en"}]
