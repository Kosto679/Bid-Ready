"""Oumi Iris decision model: a second, independent model for the judgement calls code can't check.

Two uses, both advisory checks with receipts, never the only source of truth:
  1. second_opinion(): for meaning-based rules (past projects, team), does the company as described meet it?
     Shown next to our own reading; it never changes the verdict.
  2. letter_claims(): is each sentence of Gemini's letter rewrite supported by the checked draft?
     An unsupported sentence rejects the rewrite and the checked draft is used.

API: POST https://inference.oumi.ai/v1/systemone, header X-API-Key, body {model, state, questions}.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from . import config

URL = "https://inference.oumi.ai/v1/systemone"
MEANING_RULES = ("experience", "team")  # rule ids starting with these are judged by meaning, not by a number


class NotConfigured(RuntimeError):
    pass


def configured() -> tuple[bool, str]:
    if config.offline():
        return False, "offline mode (BIDREADY_OFFLINE=1)"
    for k in ("OUMI_API_KEY", "OUMI_PROJECT_ID"):
        if not os.environ.get(k):
            return False, f"{k} is not set in .env"
    return True, ""


def model_name() -> str:
    return f"projects/{os.environ.get('OUMI_PROJECT_ID', '')}/models/{os.environ.get('OUMI_MODEL') or 'iris-latest'}"


def ask(state: str, questions: dict[str, dict], timeout: float = 45) -> dict[str, Any]:
    ok, why = configured()
    if not ok:
        raise NotConfigured(why)
    with httpx.Client(timeout=timeout) as c:
        r = c.post(URL, headers={"Content-Type": "application/json", "X-API-Key": os.environ["OUMI_API_KEY"]},
                   json={"model": model_name(), "state": state, "questions": questions})
        r.raise_for_status()
        return (r.json() or {}).get("answers") or {}


def _prob(a: Any) -> float | None:
    """P(true) from a noul answer; tolerant of a bare number or a nested object."""
    v = a.get("noul") if isinstance(a, dict) else a
    if isinstance(v, dict):
        v = v.get("true", v.get("probability"))
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


def _noul(instructions: str, true: str, false: str) -> dict:
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


# ---- 1. second opinion on meaning-based rules ----------------------------------------------------

def _company(profile: dict) -> dict:
    keep = ("name", "summary", "size", "certificates", "public_sector_projects_last_5y", "declarations")
    return {k: profile.get(k) for k in keep if profile.get(k) not in (None, "", [])}


def second_opinion(rows: list[dict], profile: dict, asker=None) -> dict[str, dict]:
    """{rule_id: {"p_meets", "opinion", "agrees"}} for meaning-based rule rows."""
    todo = [r for r in rows if r.get("id", "").startswith(MEANING_RULES) and not r.get("declared")]
    if not todo:
        return {}
    reqs = "\n".join(f"[{r['id']}] {r['title']}. {r.get('notes') or ''} {(r.get('citation') or {}).get('quote') or ''}".strip() for r in todo)
    state = ("A public-tender eligibility check. COMPANY (as the company described itself):\n"
             + json.dumps(_company(profile), ensure_ascii=False) + "\n\nREQUIREMENTS from the tender:\n" + reqs)
    qs = {re.sub(r"\W", "_", r["id"]): _noul(
        f"Judge requirement [{r['id']}] only. Using only what the company states, does it meet this requirement? "
        "If the company gives no information about it, answer false.",
        "The company's stated facts show it meets the requirement.",
        "The stated facts don't show it meets the requirement, or say nothing about it.") for r in todo}
    answers = (asker or ask)(state, qs)
    out = {}
    for r in todo:
        p = _prob(answers.get(re.sub(r"\W", "_", r["id"])))
        if p is None:
            continue
        opinion = "meets" if p >= 0.7 else "missing" if p <= 0.3 else "unclear"
        out[r["id"]] = {"p_meets": round(p, 3), "opinion": opinion,
                        "agrees": opinion == r["status"] or (r["status"] == "unclear" and opinion != "meets")}
    return out


# ---- 2. sentence-by-sentence claim check on the letter rewrite -----------------------------------

def sentences(md: str, limit: int = 40) -> list[str]:
    """Content sentences of a Markdown letter: no headings, placeholders or one-word lines."""
    text = re.sub(r"(?m)^\s*#.*$|^\s*[-*]\s*", "", md)
    parts = re.split(r"(?<=[.;·!?])\s+|\n+", text)
    keep = [p.strip() for p in parts if len(p.strip()) >= 25 and not re.fullmatch(r"\[[^\]]*\]\.?", p.strip())]
    return keep[:limit]


def letter_claims(candidate: str, draft: str, asker=None) -> dict:
    """{"ok", "checked", "unsupported": [{sentence, p}]}. ok is False if any sentence is likely unsupported."""
    sents = sentences(candidate)
    if not sents:
        return {"ok": True, "checked": 0, "unsupported": []}
    state = ("REFERENCE LETTER (checked facts):\n" + draft + "\n\nREWRITTEN LETTER, sentence by sentence:\n"
             + "\n".join(f"[s{i}] {s}" for i, s in enumerate(sents)))
    qs = {f"s{i}": _noul(f"Judge sentence [s{i}] only. Is every fact, number, date, commitment and capability in it stated in "
                         "the reference letter? Rewording, tone and politeness are fine.",
                         "Everything the sentence claims is in the reference letter.",
                         "The sentence adds a fact, commitment or capability that the reference letter doesn't state.")
          for i in range(len(sents))}
    answers = (asker or ask)(state, qs)
    bad = []
    for i, s in enumerate(sents):
        p = _prob(answers.get(f"s{i}"))
        if p is not None and p < 0.3:
            bad.append({"sentence": s, "p_supported": round(p, 3)})
    return {"ok": not bad, "checked": len(sents), "unsupported": bad}
