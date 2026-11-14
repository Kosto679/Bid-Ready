"""Bid-Ready agent: plans the curated flow over the six tools. It never self-certifies; readiness
comes only from verifier.run_state().
"""
from __future__ import annotations

from . import cpv, eligibility, letter, pack, scoring, ted, verifier
from .receipts import new_run_id

DEMO_NOTICE = "769674-2026"
FETCH = 100  # notices pulled from TED per search; all are scored before the top N are shown


def default_value_max(profile: dict) -> float | None:
    """Half the 3-year turnover: tenders typically ask for turnover of ~200% of the value to qualify alone."""
    t = profile.get("turnover_2023_2025_total_eur")
    return round(t / 2, -3) if t else None


def in_value_range(notice: dict, vmin: float | None, vmax: float | None) -> bool | None:
    """True/False, or None when TED has no estimated value (kept, but flagged)."""
    v = notice.get("estimated_value")
    if v is None:
        return None
    return (vmin is None or v >= vmin) and (vmax is None or v <= vmax)


def shortlist(profile: dict, run_id: str | None = None, limit: int = 8,
              value_min: float | None = None, value_max: float | None = None) -> dict:
    """Search TED in the profile's CPV divisions, score every result, keep those inside the estimated-value
    range (unknown values are kept and flagged), return the best `limit` (+ the demo tender)."""
    run_id = run_id or new_run_id()
    divisions = sorted({cpv.digits(c)[:2] for c in profile.get("cpv_codes") or [] if len(cpv.digits(c)) >= 2}) or ["72"]
    found = ted.find_tenders(limit=FETCH, run_id=run_id, include=[DEMO_NOTICE], cpv_divisions=divisions)
    scored = scoring.score_tenders(found["notices"], profile, run_id=run_id)["scored"]
    kept, hidden = [], []
    for s in scored:
        ok = in_value_range(s, value_min, value_max)
        (hidden if ok is False else kept).append({**s, "value_unknown": ok is None})
    top = kept[:limit]
    demo = next((s for s in scored if s["publication_number"] == DEMO_NOTICE), None)
    if demo and not any(t["publication_number"] == DEMO_NOTICE for t in top):
        outside = in_value_range(demo, value_min, value_max) is False
        # shown for the demo even though it didn't make the list
        top.append({**demo, "pinned": True, "pinned_reason": "outside your value range" if outside else "not in your top 8"})
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
            "filter": {"value_min": value_min, "value_max": value_max, "hidden": len(hidden),
                       "unknown_value": sum(k["value_unknown"] for k in kept),
                       "default_max": default_value_max(profile)},
        },
        "receipts": [found["receipt"]],
    }


def prepare_bid(notice_id: str, profile: dict, run_id: str | None = None, with_letter: bool = True) -> dict:
    """Eligibility + verify (about 1 s). The letter's Gemini rewrite takes ~15 s, so the UI asks for it separately."""
    run_id = run_id or new_run_id()
    elig = eligibility.check_eligibility(notice_id, profile, run_id=run_id)  # includes verify()
    out = {"run_id": run_id, "eligibility": elig}
    if with_letter:
        out["letter"] = draft_letter(run_id, notice_id, profile, elig)
    out["state"] = verifier.run_state(run_id)
    return out


def draft_letter(run_id: str, notice_id: str, profile: dict, elig: dict | None = None) -> dict:
    if notice_id != DEMO_NOTICE:
        # The consortium letter needs the tender's scope and figures, which we only have checked for ΚτΠ.
        return {"markdown": None, "source": "unavailable",
                "note": "The consortium letter and handover pack need a full document pack; for now that's ΚτΠ only."}
    elig = elig or eligibility.load_report(run_id)
    if not elig:
        raise ValueError(f"no eligibility report for {run_id}; run prepare first")
    return letter.draft_cover_letter(notice_id, profile, elig, run_id=run_id)


def handover(run_id: str, notice_id: str) -> dict:
    return pack.build_pack(run_id, notice_id)
