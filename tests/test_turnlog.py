import json
from pathlib import Path

import pytest

from hrag.ports import Turn
from hrag.turnlog import BigQueryTurnLog, JsonlTurnLog


def _turn(turn_id: str = "t1") -> Turn:
    return Turn(
        turn_id=turn_id,
        channel="web",
        language="fi",
        question_hash="deadbeef",
        passage_ids=["1", "2"],
        cited_ids=["1"],
        model="template",
        guard="ok",
        latency_ms={"guard": 1, "retrieve": 2, "generate": 3, "log": 0, "total": 6},
        outcome="answered",
    )


def test_jsonl_turn_log_appends_and_never_carries_question_text(tmp_path: Path):
    path = tmp_path / "turns" / "turns.jsonl"
    log = JsonlTurnLog(path=path)

    log.write(_turn("t1"))
    log.write(_turn("t2"))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["turn_id"] == "t1"
    assert row["question_hash"] == "deadbeef"
    assert "question" not in row
    assert all("question" not in key for key in row if key != "question_hash")


def test_jsonl_turn_log_creates_parent_dirs(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "turns.jsonl"
    JsonlTurnLog(path=path).write(_turn())
    assert path.exists()


class FakeBQClient:
    def __init__(self, errors: list | None = None) -> None:
        self.errors = errors or []
        self.calls: list[tuple[str, list[dict]]] = []

    def insert_rows_json(self, table: str, rows: list[dict]) -> list:
        self.calls.append((table, rows))
        return self.errors


def test_bigquery_turn_log_inserts_row():
    client = FakeBQClient()
    log = BigQueryTurnLog(client=client, table="proj.ds.turns")

    log.write(_turn("t1"))

    assert len(client.calls) == 1
    table, rows = client.calls[0]
    assert table == "proj.ds.turns"
    assert rows[0]["turn_id"] == "t1"
    assert "question" not in rows[0]


def test_bigquery_turn_log_raises_on_insert_errors():
    client = FakeBQClient(errors=[{"index": 0, "errors": ["bad row"]}])
    log = BigQueryTurnLog(client=client, table="proj.ds.turns")

    with pytest.raises(RuntimeError):
        log.write(_turn())
