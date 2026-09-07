"""Vertex AI Search retriever. `LocalRetriever` in `local.py` is the offline
twin the API and eval harness use by default; this one is selected with
HRAG_RETRIEVER=vertex. The Google client is imported lazily so the default
install and offline tests never need the `gcp` extra.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from hrag.ports import Passage

MAX_RESULTS = 50


class SearchClient(Protocol):
    def search(self, request: dict[str, Any]) -> Any: ...


class VertexSearchRetriever:
    def __init__(self, client: SearchClient | None = None, serving_config: str | None = None) -> None:
        self._client = client
        self.serving_config = serving_config or os.environ.get("HRAG_VERTEX_SERVING_CONFIG", "")

    def _get_client(self) -> SearchClient:
        if self._client is None:
            from google.cloud import discoveryengine_v1  # imported lazily: gcp extra only

            self._client = discoveryengine_v1.SearchServiceClient()
        return self._client

    def search(self, query: str, k: int) -> list[Passage]:
        capped = min(k, MAX_RESULTS)
        client = self._get_client()
        request = {"serving_config": self.serving_config, "query": query, "page_size": capped}
        results = client.search(request)
        return [_to_passage(r) for r in results][:capped]


def _to_passage(result: Any) -> Passage:
    doc = result.document
    data: dict[str, Any] = getattr(doc, "struct_data", None) or {}
    return Passage(
        id=str(doc.id),
        title=data.get("name", ""),
        text=data.get("content", ""),
        source_url=data.get("url", ""),
        score=float(getattr(result, "relevance_score", 0.0) or 0.0),
    )
