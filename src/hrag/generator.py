"""Answer generation. TemplateGenerator is deterministic and needs no model;
GeminiGenerator prompts Gemini with citation-tagged passages and parses the
result, dropping any cited id that was not actually retrieved.
"""

from __future__ import annotations

import os
import re
from typing import Any, Protocol

from hrag.ports import Answer, Passage

TOP_N = 3
DEFAULT_MODEL = "gemini-2.5-flash"
REGION = "europe-north1"

CITATION_RE = re.compile(r"\[([A-Za-z0-9_-]+)\]")

SYSTEM_PROMPT = (
    "You are a Helsinki public-service assistant. Answer only from the passages "
    "below, in the language of the question. Cite every fact with its passage id "
    "in square brackets, e.g. [12]. If the passages do not answer the question, "
    "say you don't know."
)

NO_ANSWER_TEXT = "No matching service point found."


class TemplateGenerator:
    """Formats the top retrieved passages as lines, no model call."""

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        if not passages:
            return Answer(text=NO_ANSWER_TEXT, citations=(), model="template", no_answer=True)

        top = passages[:TOP_N]
        text = "\n".join(f"{p.title}, {p.text} [{p.id}]" for p in top)
        return Answer(text=text, citations=tuple(p.id for p in top), model="template", no_answer=False)


class GenerativeModel(Protocol):
    def generate_content(self, prompt: str) -> Any: ...


class GeminiGenerator:
    def __init__(self, client: GenerativeModel | None = None, model_name: str | None = None) -> None:
        self._client = client
        self.model_name = model_name or os.environ.get("HRAG_GEMINI_MODEL", DEFAULT_MODEL)

    def _get_client(self) -> GenerativeModel:
        if self._client is None:
            from google import genai  # imported lazily: gcp extra only

            client = genai.Client(vertexai=True, location=REGION)
            self._client = _GenAIAdapter(client, self.model_name)
        return self._client

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        if not passages:
            return Answer(text=NO_ANSWER_TEXT, citations=(), model=self.model_name, no_answer=True)

        prompt = _build_prompt(question, passages)
        response = self._get_client().generate_content(prompt)
        text = _extract_text(response)

        valid_ids = {p.id for p in passages}
        cited = tuple(dict.fromkeys(m for m in CITATION_RE.findall(text) if m in valid_ids))
        return Answer(text=text, citations=cited, model=self.model_name, no_answer=False)


def _build_prompt(question: str, passages: list[Passage]) -> str:
    blocks = "\n".join(f'<passage id="{p.id}">{p.text}</passage>' for p in passages)
    return f"{SYSTEM_PROMPT}\n\n{blocks}\n\nQuestion: {question}"


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if not isinstance(text, str):
        raise TypeError("generator response has no text")
    return text


class _GenAIAdapter:
    """Adapts the google-genai client's call shape to `generate_content`."""

    def __init__(self, client: Any, model_name: str) -> None:
        self._client = client
        self._model_name = model_name

    def generate_content(self, prompt: str) -> Any:
        return self._client.models.generate_content(model=self._model_name, contents=prompt)
