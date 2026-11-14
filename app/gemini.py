"""Gemini on Vertex AI (the contest's Google Cloud project). Used by the eval harness only.

Auth is Application Default Credentials (`gcloud auth application-default login`) or a
service-account file in GOOGLE_APPLICATION_CREDENTIALS. Never a key in the repo.
"""
from __future__ import annotations

import json
import os
from typing import Any

from . import config  # noqa: F401  (loads .env before GEMINI_MODEL is read)

MODEL =os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"], "description": "The answer, or null if the text does not state it."},
        "quote": {"type": ["string", "null"], "description": "Exact words copied from the text that support the answer."},
    },
    "required": ["value", "quote"],
}

SYSTEM = (
    "You extract facts from Greek public-procurement documents for a bid-preparation tool. "
    "Answer only from the text you are given. If the text does not state the fact, return value null; "
    "do not compute it from other figures unless the question asks you to. "
    "Copy the supporting quote exactly as it appears in the text."
)


class NotConfigured(RuntimeError):
    pass


def fast_thinking():
    """Low thinking for simple extraction tasks: same answers in our tests, ~2.5x faster.
    The model check (ask) keeps the model's default so its accuracy numbers stay comparable."""
    from google.genai import types

    return types.ThinkingConfig(thinking_level="low")


def configured() -> tuple[bool, str]:
    if os.environ.get("BIDREADY_OFFLINE", "0") == "1":
        return False, "offline mode (BIDREADY_OFFLINE=1)"
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return False, "GOOGLE_CLOUD_PROJECT is not set in .env"
    return True, ""


_client = None


def client():
    global _client
    ok, why = configured()
    if not ok:
        raise NotConfigured(why)
    if _client is None:
        from google import genai

        _client = genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        )
    return _client


PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": ["string", "null"], "description": "Company name exactly as written, or null."},
        "size": {"type": ["integer", "null"], "description": "Number of people, only if stated."},
        "city": {"type": ["string", "null"], "description": "City in English (e.g. Athens), only if stated."},
        "nuts_or_country": {"type": ["string", "null"], "description": "Greek NUTS-2 code (EL30 Attica, EL52 Central Macedonia, EL63 Western Greece, EL43 Crete, ...) if the city is in Greece, else ISO3 country code, else null."},
    },
    "required": ["name", "size", "city", "nuts_or_country"],
}

PROFILE_SYSTEM = (
    "You read a short company description for a public-tender tool. Extract only what is stated. "
    "Use null for anything not stated; never guess a size or a name."
)

_profile_cache: dict[str, dict] = {}


def extract_profile(description: str, model: str | None = None) -> dict:
    """{"name", "size", "city", "nuts_or_country"} from the description (validate before use). Cached per text."""
    from google.genai import types

    key = description.strip()
    if key in _profile_cache:
        return _profile_cache[key]
    resp = client().models.generate_content(
        model=model or MODEL,
        contents=f"COMPANY DESCRIPTION:\n<<<\n{description}\n>>>",
        config=types.GenerateContentConfig(
            system_instruction=PROFILE_SYSTEM,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=PROFILE_SCHEMA,
            thinking_config=fast_thinking(),
        ),
    )
    try:
        out = json.loads(resp.text or "{}")
    except json.JSONDecodeError:
        out = {}
    _profile_cache[key] = out
    return out


CPV_SCHEMA = {
    "type": "object",
    "properties": {
        "codes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "An 8-digit code copied exactly from the list."},
                    "reason": {"type": "string", "description": "Under 12 words, quoting the words from the description that justify it."},
                },
                "required": ["code", "reason"],
            },
        }
    },
    "required": ["codes"],
}

CPV_SYSTEM = (
    "You assign EU CPV (Common Procurement Vocabulary) codes to a company so it can find public tenders it could win. "
    "Choose ONLY codes from the list provided, copied exactly. Pick 2 to 6 codes for what the company actually sells, "
    "most specific first; include the broad division code only if it adds coverage. Do not pick codes for its clients' "
    "industries (a software studio serving hotels is not a hotel). Give each a short reason quoting the description."
)

_cpv_cache: dict[str, list[dict]] = {}


def suggest_cpv(description: str, model: str | None = None) -> list[dict]:
    """Returns [{"code", "reason"}] straight from the model (validate against app.cpv before use). Cached per text."""
    from google.genai import types

    from . import cpv

    key = description.strip()
    if key in _cpv_cache:
        return _cpv_cache[key]
    resp = client().models.generate_content(
        model=model or MODEL,
        contents=f"CPV CODES YOU MAY USE:\n{cpv.prompt_list()}\n\nCOMPANY DESCRIPTION:\n<<<\n{description}\n>>>",
        config=types.GenerateContentConfig(
            system_instruction=CPV_SYSTEM,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=CPV_SCHEMA,
            thinking_config=fast_thinking(),
        ),
    )
    try:
        out = json.loads(resp.text or "{}").get("codes", [])
    except json.JSONDecodeError:
        out = []
    _cpv_cache[key] = out
    return out


def ask(question: str, context: str, model: str | None = None) -> dict[str, Any]:
    """One extraction: returns {"value", "quote", "raw", "model"}. Raises on transport errors."""
    from google.genai import types

    resp = client().models.generate_content(
        model=model or MODEL,
        contents=f"TEXT:\n<<<\n{context}\n>>>\n\nQUESTION: {question}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=ANSWER_SCHEMA,
        ),
    )
    raw = resp.text or ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"value": None, "quote": None}
    return {"value": data.get("value"), "quote": data.get("quote"), "raw": raw, "model": model or MODEL}
