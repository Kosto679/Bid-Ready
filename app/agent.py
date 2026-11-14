"""Bid-Ready agent: plans the curated flow over the six tools. It never self-certifies; readiness
comes only from verifier.run_state().
"""
from __future__ import annotations

from . import cpv, eligibility, letter, pack, scoring, ted, verifier
from .receipts import new_run_id

DEMO_NOTICE = "769674-2026"
FETCH = 100  # notices pulled from TED per search; all are scored before the top N are shown


def shortlist(profile: dict, run_id: str | None = None, limit: int = 8) -> dict:
    """Search TED in the profile's CPV divisions, score every result, return the best `limit` (+ the demo tender)."""
    run_id = run_id or new_run_id()
    divisions = sorted({cpv.digits(c)[:2] for c in profile.get("cpv_codes") or [] if len(cpv.digits(c)) >= 2}) or ["72"]
    found = ted.find_tenders(limit=FETCH, run_id=run_id, include=[DEMO_NOTICE], cpv_divisions=divisions)
    scored = scoring.score_tenders(found["notices"], profile, run_id=run_id)["scored"]
    top = scored[:limit]
    demo = next((s for s in scored if s["publication_number"] == DEMO_NOTICE), None)
    if demo and demo not in top:
        demo = {**demo, "pinned": True}  # shown for the demo even though it didn't make the top N
        top.append(demo)
    return {
        "run_id": run_id,
        "source": found["source"],
        "matches": top,
        "searched": {
            "divisions": [{"code": d, "label": cpv.division(d)} for d in divisions],
            "query": found["query"],
            "total_on_ted": found["total"],
            "scored": len(scored),
            "shown": len(top),
        },
        "receipts": [found["receipt"]],
    }


def prepare_bid(notice_id: str, profile: dict, run_id: str | None = None) -> dict:
    run_id = run_id or new_run_id()
    elig = eligibility.check_eligibility(notice_id, profile, run_id=run_id)  # includes verify()
    if notice_id == DEMO_NOTICE:
        let = letter.draft_cover_letter(notice_id, profile, elig, run_id=run_id)
    else:
        # The consortium letter needs the tender's scope and figures, which we only have checked for ΚτΠ.
        let = {"markdown": None, "source": "unavailable",
               "note": "The consortium letter and handover pack need a full document pack; for now that's ΚτΠ only."}
    return {"run_id": run_id, "eligibility": elig, "letter": let, "state": verifier.run_state(run_id)}


def handover(run_id: str, notice_id: str) -> dict:
    return pack.build_pack(run_id, notice_id)
