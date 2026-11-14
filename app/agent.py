"""Bid-Ready agent: plans the curated flow over the six tools. It never self-certifies; readiness
comes only from verifier.run_state().
"""
from __future__ import annotations

from . import eligibility, letter, pack, scoring, ted, verifier
from .receipts import new_run_id

DEMO_NOTICE = "769674-2026"


def shortlist(profile: dict, run_id: str | None = None, limit: int = 8) -> dict:
    run_id = run_id or new_run_id()
    found = ted.find_tenders(limit=limit, run_id=run_id, include=[DEMO_NOTICE])
    scored = scoring.score_tenders(found["notices"], profile, run_id=run_id)
    return {"run_id": run_id, "source": found["source"], "matches": scored["scored"], "receipts": [found["receipt"], scored["receipt"]]}


def prepare_bid(notice_id: str, profile: dict, run_id: str | None = None) -> dict:
    run_id = run_id or new_run_id()
    elig = eligibility.check_eligibility(notice_id, profile, run_id=run_id)  # includes verify()
    let = letter.draft_cover_letter(notice_id, profile, elig, run_id=run_id)
    return {"run_id": run_id, "eligibility": elig, "letter": let, "state": verifier.run_state(run_id)}


def handover(run_id: str, notice_id: str) -> dict:
    return pack.build_pack(run_id, notice_id)
