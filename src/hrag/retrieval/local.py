"""Keyword retriever over the Helsinki service-point CSV. Test and offline adapter.

The Vertex AI Search adapter replaces this in the cloud; the API and eval harness
do not care which one is behind the `Retriever` port.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from hrag.ports import Passage

DATA = Path(__file__).resolve().parents[3] / "data" / "helsinki_service_points.csv"
MAX_ROWS = 50_000


class LocalRetriever:
    def __init__(self, path: Path = DATA) -> None:
        self.rows: list[dict[str, str]] = []
        with path.open(encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if i >= MAX_ROWS:
                    break
                self.rows.append(row)

    def search(self, query: str, k: int) -> list[Passage]:
        terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
        if not terms:
            return []
        scored: list[tuple[int, dict[str, str]]] = []
        for row in self.rows:
            text = " ".join(row.values()).lower()
            score = sum(1 for t in terms if t in text)
            if score:
                scored.append((score, row))
        scored.sort(key=lambda s: -s[0])
        return [_passage(r, s) for s, r in scored[:k]]


def _passage(row: dict[str, str], score: int) -> Passage:
    title = row.get("name_en") or row.get("name_fi") or row["id"]
    text = (
        f"{row.get('name_fi', '')} / {row.get('name_en', '')}. "
        f"{row.get('street_address_fi', '')}, {row.get('address_zip', '')} "
        f"{row.get('municipality', '')}. Phone {row.get('phone', '')}."
    )
    return Passage(id=row["id"], title=title, text=text, source_url=row.get("www_fi", ""), score=score)
