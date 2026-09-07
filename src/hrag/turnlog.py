"""Turn logging. `Turn` (ports.py) never carries the question text, only its
hash, so both adapters can log freely without leaking user input.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Protocol

from hrag.ports import Turn

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "turns" / "turns.jsonl"


class JsonlTurnLog:
    """Append-only local log, the default. One JSON object per line."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path

    def write(self, turn: Turn) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dataclasses.asdict(turn)) + "\n")


class RowInserter(Protocol):
    def insert_rows_json(self, table: str, rows: list[dict[str, Any]]) -> list[Any]: ...


class BigQueryTurnLog:
    """Streaming-inserts turns into BigQuery. Raises on insert errors rather
    than silently dropping a turn, matching the local adapter's durability."""

    def __init__(self, client: RowInserter | None = None, table: str | None = None) -> None:
        self._client = client
        self.table = table or os.environ.get("HRAG_BQ_TABLE", "")

    def _get_client(self) -> RowInserter:
        if self._client is None:
            from google.cloud import bigquery  # imported lazily: gcp extra only

            self._client = bigquery.Client()
        return self._client

    def write(self, turn: Turn) -> None:
        client = self._get_client()
        errors = client.insert_rows_json(self.table, [dataclasses.asdict(turn)])
        if errors:
            raise RuntimeError(f"bigquery insert errors: {errors}")
