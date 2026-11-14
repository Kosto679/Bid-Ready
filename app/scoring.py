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
        "band": band(fit),
        "factors": {"cpv": round(cpv, 3), "value_fit": round(val, 3), "place": place, "deadline": round(dl, 3), "days_to_deadline": days},
        "explain": explain(notice, profile, cpv, matches, val, place, days),
        "reason": reason,
    }


# Colour bands for the 0-100 fit score (and 0-1 factors x 100).
def band(score: float) -> str:
    return "good" if score >= 70 else ("fair" if score >= 40 else "weak")


CPV_DIVISIONS = {
    "03": "agriculture and food raw materials", "09": "fuels and energy", "22": "printed matter", "30": "office and computing machinery",
    "31": "electrical machinery", "32": "radio, TV and communication equipment", "33": "medical equipment", "34": "transport equipment",
    "35": "security and defence equipment", "38": "laboratory and precision equipment", "39": "furniture and furnishings",
    "45": "construction work", "48": "software packages and information systems", "50": "repair and maintenance",
    "51": "installation services", "64": "postal and telecommunications", "71": "architecture and engineering",
    "72": "IT services: consulting, software development, Internet and support", "73": "research and development",
    "79": "business services", "80": "education and training", "90": "environmental services", "92": "recreational and cultural services",
}


def division_name(code: str) -> str:
    return CPV_DIVISIONS.get(_digits(code)[:2], "other")


def explain(notice: dict, profile: dict, cpv: float, matches: int, val: float, place: float, days: int | None) -> dict:
    codes = list(dict.fromkeys(_digits(c) for c in notice.get("classification_cpv") or [] if _digits(c)))
    mine = sorted({_digits(c)[:2] for c in profile.get("cpv_codes") or [] if len(_digits(c)) >= 2})
    divs = sorted({c[:2] for c in codes})
    if not mine:
        cpv_why = "We couldn't guess any CPV codes from your description, so nothing can match."
    elif not codes:
        cpv_why = "TED lists no CPV codes for this notice."
    else:
        cpv_why = (f"{matches} of the tender's {len(codes)} code{'s' if len(codes) != 1 else ''} {'falls' if matches == 1 else 'fall'} in your division"
                   f"{'s' if len(mine) > 1 else ''} ({', '.join(mine)}: {division_name(mine[0] + '000000')}). "
                   + ("Every code is yours: this is squarely your kind of work." if cpv == 1 else
                      f"The rest are in {', '.join(division_name(d + '000000') for d in divs if d not in mine)[:160]}: the buyer wants more than IT."
                      if matches else "None of the codes are in your field."))
    v, t = notice.get("estimated_value"), profile.get("turnover_2023_2025_total_eur")
    if t is None:
        val_why = "You didn't give your turnover, so this counts as 0."
    elif not v:
        val_why = "TED shows no value for this tender, so this counts as 0."
    else:
        val_why = (f"TED value {_eur(v)}. A rough rule of thumb is a 3-year turnover of twice the value ({_eur(2 * v)}). "
                   f"You have {_eur(t)}, {val:.0%} of that." + (" TED's value may include options, so the real bar can be lower." if val < 1 else ""))
    places = ", ".join((notice.get("place_of_performance") or [])[:3]) or "not given"
    place_why = (f"The work is in Greece ({places}) and so are you." if place else
                 f"The work is in {places}, outside your area." if notice.get("place_of_performance") else "TED gives no place of performance.")
    if days is None:
        dl_why = "No deadline on TED."
    elif days == 0:
        dl_why = "The deadline has passed or is today."
    else:
        dl_why = (f"{days} days to prepare. 45 days or more scores full marks; "
                  + ("you have plenty of time." if days >= DEADLINE_CAP_DAYS else "a public bid usually needs several weeks." if days < 14 else "workable, but start now."))
    return {"cpv": cpv_why, "value_fit": val_why, "place": place_why, "deadline": dl_why}


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
