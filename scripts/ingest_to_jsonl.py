"""CSV to Vertex AI Search unstructured-with-metadata JSONL.

One document per line: `id`, `structData` (searchable/filterable fields), and `content`
(the plain-text rendering, base64-encoded, per the discoveryengine import schema). Reads
and writes row by row so memory use does not grow with the corpus size.

Usage: python scripts/ingest_to_jsonl.py <csv> <out.jsonl>
"""

from __future__ import annotations

import base64
import csv
import json
import sys
from pathlib import Path
from typing import Any

MAX_ROWS = 50_000


def render_text(row: dict[str, str]) -> str:
    """Plain-text rendering of a service point, used as the document body."""
    return (
        f"{row.get('name_fi', '')} / {row.get('name_en', '')}\n"
        f"{row.get('street_address_fi', '')}, {row.get('address_zip', '')} "
        f"{row.get('municipality', '')}\n"
        f"Provider: {row.get('provider_type', '')}\n"
        f"Phone: {row.get('phone', '')}\n"
        f"URL: {row.get('www_fi', '')}"
    )


def build_document(row: dict[str, str]) -> dict[str, Any]:
    text = render_text(row)
    struct_data = {
        "name_fi": row.get("name_fi", ""),
        "name_en": row.get("name_en", ""),
        "street_address_fi": row.get("street_address_fi", ""),
        "address_zip": row.get("address_zip", ""),
        "municipality": row.get("municipality", ""),
        "provider_type": row.get("provider_type", ""),
        "phone": row.get("phone", ""),
        "url": row.get("www_fi", ""),
    }
    return {
        "id": row["id"],
        "structData": struct_data,
        "content": {
            "mimeType": "text/plain",
            "rawBytes": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        },
    }


def ingest(csv_path: Path, out_path: Path) -> int:
    """Stream `csv_path` rows into one JSON document per line at `out_path`. Returns the count."""
    count = 0
    with csv_path.open(encoding="utf-8") as csv_file, out_path.open("w", encoding="utf-8") as out_file:
        for row in csv.DictReader(csv_file):
            if count >= MAX_ROWS:
                break
            out_file.write(json.dumps(build_document(row), ensure_ascii=False))
            out_file.write("\n")
            count += 1
    return count


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <csv> <out.jsonl>", file=sys.stderr)
        return 2
    csv_path, out_path = Path(argv[1]), Path(argv[2])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = ingest(csv_path, out_path)
    print(f"wrote {count} documents to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
