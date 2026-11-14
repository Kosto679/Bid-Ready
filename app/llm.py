"""Optional runtime LLM (Claude) for onboarding. Every caller has a deterministic fallback,
so the golden path and tests run with no key and no network.
"""
from __future__ import annotations

import json
import os
from typing import Any

MODEL = os.environ.get("LLM_MODEL", "claude-opus-5-5")

PROFILE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "summary", "size", "location", "nuts_or_country", "cpv_codes"],
    "properties": {
        "name": {"type": "string"},
        "summary": {"type": "string"},
        "size": {"type": ["integer", "null"]},
        "location": {"type": ["string", "null"]},
        "nuts_or_country": {"type": ["string", "null"], "description": "Greek NUTS-2 code like EL30 if the city is known, else ISO3 country like GRC"},
        "cpv_codes": {"type": "array", "items": {"type": "string"}, "description": "Likely 8-digit CPV codes, most relevant first, max 6"},
    },
}

SYSTEM = (
    "You turn a short company description into a structured profile for EU public tenders. "
    "Only state what the text supports; use null when unknown. Never invent turnover, certificates or past projects."
)


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("BIDREADY_OFFLINE", "0") != "1"


def extract_profile(lines: str) -> dict[str, Any] | None:
    if not enabled() or not lines.strip():
        return None
    import anthropic

    client = anthropic.Anthropic(timeout=30.0)
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": PROFILE_SCHEMA}},
            messages=[{"role": "user", "content": lines}],
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return None
    if resp.stop_reason == "refusal":
        return None
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
