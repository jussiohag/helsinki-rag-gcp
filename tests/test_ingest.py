import base64
import csv
import json
from pathlib import Path

from scripts.ingest_to_jsonl import build_document, ingest, render_text

ROW = {
    "id": "3",
    "name_fi": "Päiväkoti Kannel",
    "name_en": "Daycare Kannel",
    "street_address_fi": "Kannelpolku 5",
    "address_zip": "00420",
    "municipality": "",
    "provider_type": "SELF_PRODUCED",
    "latitude": "60.239895",
    "longitude": "24.879782",
    "www_fi": "https://www.hel.fi/fi/kasvatus-ja-koulutus/paivakoti-kannel",
    "phone": "+358 9 310 41627",
}


def test_render_text_contains_key_fields():
    text = render_text(ROW)
    assert "Päiväkoti Kannel" in text
    assert "Kannelpolku 5" in text
    assert "+358 9 310 41627" in text


def test_build_document_shape():
    doc = build_document(ROW)
    assert doc["id"] == "3"
    assert doc["structData"] == {
        "name_fi": "Päiväkoti Kannel",
        "name_en": "Daycare Kannel",
        "street_address_fi": "Kannelpolku 5",
        "address_zip": "00420",
        "municipality": "",
        "provider_type": "SELF_PRODUCED",
        "phone": "+358 9 310 41627",
        "url": "https://www.hel.fi/fi/kasvatus-ja-koulutus/paivakoti-kannel",
    }
    assert doc["content"]["mimeType"] == "text/plain"
    decoded = base64.b64decode(doc["content"]["rawBytes"]).decode("utf-8")
    assert decoded == render_text(ROW)


def test_ingest_streams_one_line_per_row(tmp_path: Path):
    csv_path = tmp_path / "rows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ROW.keys()))
        writer.writeheader()
        writer.writerow(ROW)
        writer.writerow({**ROW, "id": "5", "name_fi": "Päiväkoti Kaunokki"})

    out_path = tmp_path / "documents.jsonl"
    count = ingest(csv_path, out_path)

    assert count == 2
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    ids = [json.loads(line)["id"] for line in lines]
    assert ids == ["3", "5"]


def test_ingest_respects_max_rows(tmp_path: Path, monkeypatch):
    import scripts.ingest_to_jsonl as mod

    csv_path = tmp_path / "rows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ROW.keys()))
        writer.writeheader()
        for i in range(5):
            writer.writerow({**ROW, "id": str(i)})

    monkeypatch.setattr(mod, "MAX_ROWS", 3)
    out_path = tmp_path / "documents.jsonl"
    count = mod.ingest(csv_path, out_path)

    assert count == 3
