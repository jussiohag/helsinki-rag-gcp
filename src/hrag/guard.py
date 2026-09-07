"""Input guard. HeuristicGuard runs locally with no network; ModelArmorGuard
calls Google's Model Armor API and fails closed on any transport error.
"""

from __future__ import annotations

import os

import httpx

from hrag.ports import GuardResult

MAX_CHARS = 2000

INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "you are now",
    "system prompt",
    "reveal your instructions",
)


class HeuristicGuard:
    def check(self, text: str) -> GuardResult:
        if len(text) > MAX_CHARS:
            return GuardResult(allowed=False, reason=f"input exceeds {MAX_CHARS} characters")
        lowered = text.lower()
        for phrase in INJECTION_PHRASES:
            if phrase in lowered:
                return GuardResult(allowed=False, reason=f"blocked phrase: {phrase}")
        return GuardResult(allowed=True)


class ModelArmorGuard:
    """Calls the Model Armor sanitizeUserPrompt REST endpoint. Any transport or
    API error blocks the input rather than letting it through unchecked."""

    def __init__(self, client: httpx.Client | None = None, template: str | None = None) -> None:
        self._client = client
        self.template = template or os.environ.get("HRAG_MODEL_ARMOR_TEMPLATE", "")

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url="https://modelarmor.googleapis.com")
        return self._client

    def check(self, text: str) -> GuardResult:
        try:
            client = self._get_client()
            response = client.post(
                f"/v1/{self.template}:sanitizeUserPrompt",
                json={"userPromptData": {"text": text}},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return GuardResult(allowed=False, reason=f"model armor error: {exc}")

        match_state = data.get("sanitizationResult", {}).get("filterMatchState", "NO_MATCH_FOUND")
        if match_state != "NO_MATCH_FOUND":
            return GuardResult(allowed=False, reason=f"model armor match: {match_state}")
        return GuardResult(allowed=True)
