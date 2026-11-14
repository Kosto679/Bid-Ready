"""score_tenders: visible fit formula on TED metadata + company profile only (docs/04-scoring.md).

Never reads requirements.json.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from . import config
from .receipts import new_run_id, write_receipt

DEADLINE_CAP_DAYS = 45  # cap so very distant deadlines do not dominate the score


def _digits(code: str) -> str:
    return re.sub(r"\D", "", code.split("-")[0])


def cpv_factor(notice_cpvs: list[str], profile_cpvs: list[str]) -> tuple[float, int]:
    prof = {_digits(c)[:2] for c in profile_cpvs if len(_digits(c)) >= 2}
    if not prof:
        return 0.0, 0
    codes = list(dict.fromkeys(_digits(c) for c in notice_cpvs if _digits(c)))
    matches = sum(1 for c in codes if c[:2] in prof)
    return matches / max(len(codes), 1), matches


def value_factor(ted_value: float | None, turnover: float | None) -> float:
    if turnover is None or not ted_value:
        return 0.0
    need = 2.0 * ted_value  # rough 200% heuristic on the TED value (may include options)
    return min(1.0, turnover / need)


def _is_greece(profile: dict) -> bool:
    code = (profile.get("nuts_or_country") or "").upper()
    if code == "GRC" or code.startswith("EL"):
        return True
    loc = (profile.get("location") or "").lower()
    return any(k in loc for k in ("greece", "ελλάδα", "athens", "αθήνα", "thessaloniki", "θεσσαλονίκη"))


def place_factor(places: list[str], profile: dict) -> float:
    if not places:
        return 0.0
    nuts = (profile.get("nuts_or_country") or "").upper()
    if nuts.startswith("EL") and len(nuts) > 2 and any(p.upper().startswith(nuts) for p in places):
        return 1.0
    if _is_greece(profile) and any(p.upper().startswith("EL") or p.upper() == "GRC" for p in places):
        return 1.0
    return 0.0


def days_to(deadline: str | None, today: date) -> int | None:
    if not deadline:
        return None
    return max(0, (date.fromisoformat(deadline[:10]) - today).days)


def deadline_factor(days: int | None) -> float:
    if days is None:
        return 0.0
    return min(days, DEADLINE_CAP_DAYS) / DEADLINE_CAP_DAYS


def _eur(v: float | None) -> str:
    return "unknown" if v is None else f"€{v:,.0f}"


def score_one(notice: dict, profile: dict, today: date) -> dict:
    cpv, matches = cpv_factor(notice.get("classification_cpv") or [], profile.get("cpv_codes") or [])
    turnover = profile.get("turnover_2023_2025_total_eur")
    val = value_factor(notice.get("estimated_value"), turnover)
    place = place_factor(notice.get("place_of_performance") or [], profile)
    days = days_to(notice.get("deadline_date"), today)
    dl = deadline_factor(days)
    fit = round(100 * (0.25 * cpv + 0.25 * val + 0.25 * place + 0.25 * dl))

    cpv_txt = "matches" if matches else "does not match"
    if matches and cpv < 1:
        cpv_txt = f"partly matches ({matches} of {len(set(_digits(c) for c in notice.get('classification_cpv') or []))} codes)"
    place_txt = "Greece, like you" if place else ("unknown" if not notice.get("place_of_performance") else "outside your area")
    days_txt = "no deadline" if days is None else (f"{days} days" + (", capped at 45 for scoring" if days > DEADLINE_CAP_DAYS else ""))
    reason = (
        f"CPV {cpv_txt} your profile; the TED value is {_eur(notice.get('estimated_value'))} versus your "
        f"{_eur(turnover) if turnover is not None else 'unknown'} 3-year turnover; place is {place_txt}; "
        f"the deadline is {notice.get('deadline_date') or 'unknown'} ({days_txt})."
    )
    return {
        **notice,
        "fit_score": fit,
        "factors": {"cpv": round(cpv, 3), "value_fit": round(val, 3), "place": place, "deadline": round(dl, 3), "days_to_deadline": days},
        "reason": reason,
    }


def score_tenders(notices: list[dict], profile: dict, run_id: str | None = None) -> dict[str, Any]:
    run_id = run_id or new_run_id()
    today = config.now_athens().date()
    scored = [score_one(n, profile, today) for n in notices]
    scored.sort(key=lambda s: (-s["fit_score"], s.get("deadline_date") or "9999", s.get("publication_number") or ""))
    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"score_tenders:{run_id}:{'|'.join(s['publication_number'] for s in scored)}:{profile.get('name')}",
        "action": "score_tenders",
        "intent": {"formula": "round(100*(0.25*cpv + 0.25*value_fit + 0.25*place + 0.25*deadline))", "today": today.isoformat()},
        "tool_call": {"name": "score_tenders", "arguments": {"notices": len(notices), "profile": profile.get("name")}},
        "tool_response": {"ranked": [{"publication_number": s["publication_number"], "fit_score": s["fit_score"]} for s in scored]},
        "status": "RECORDED",
        "reason": "Shortlist score, not eligibility.",
    })
    return {"run_id": run_id, "scored": scored, "receipt": receipt}
