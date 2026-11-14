"""MCP server (FastMCP, stdio) exposing the six Bid-Ready tools. Run: python -m app.mcp_server

Every tool writes a receipt before returning; results carry `receipt` / `receipts`.
"""
from __future__ import annotations

import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import eligibility as E
from . import letter as L
from . import pack as P
from . import scoring as S
from . import ted as T
from . import verifier as V
from .profile import DEMO_ANSWERS, DEMO_LINES, onboard

mcp = FastMCP("bid-ready")


def _demo_profile() -> dict:
    return onboard(DEMO_LINES, DEMO_ANSWERS)["profile"]


@mcp.tool()
def find_tenders(query: str | None = None, place: str = "EL*", cpv: str = "72*", deadline_from: str = "20261116",
                 limit: int = 10, run_id: str | None = None, cpv_divisions: list[str] | None = None,
                 value_min: float | None = None, value_max: float | None = None) -> dict[str, Any]:
    """Search TED for open tenders (TED Search API v3, no key). Filters: place (NUTS, e.g. EL*), CPV (72*) or
    cpv_divisions (["72","48"]), deadline_from (YYYYMMDD), estimated value range (value_min/value_max, EUR; notices
    with no value are kept and flagged). Falls back to the local cache and marks the live hop UNVERIFIED."""
    res = T.find_tenders(query, place, cpv, deadline_from, max(limit, 100) if (value_min or value_max) else limit,
                         run_id=run_id, include=["769674-2026"], cpv_divisions=cpv_divisions)
    if value_min is not None or value_max is not None:
        kept = []
        for n in res["notices"]:
            v = n.get("estimated_value")
            if v is None:
                kept.append({**n, "value_unknown": True})
            elif (value_min is None or v >= value_min) and (value_max is None or v <= value_max):
                kept.append(n)
        res = {**res, "notices": kept[:limit], "filtered_out": len(res["notices"]) - len(kept)}
    return res


@mcp.tool()
def scan_khmdhs(title: str | None = None, cpv_codes: list[str] | None = None, deadline_from: str | None = None,
                deadline_to: str | None = None, cost_min: float | None = None, cost_max: float | None = None,
                limit: int = 25) -> dict[str, Any]:
    """Scan ΚΗΜΔΗΣ, the Greek central procurement register (every Greek public tender, including ones not on TED).
    Filters: title words, CPV codes with check digit (e.g. "72000000-5"), submission deadline range
    ("YYYY-MM-DD" or "YYYY-MM-DD HH:mm"), cost excl. VAT range in EUR. Each result has an ΑΔΑΜ id that
    read_rules and check_eligibility accept. Defaults to tenders still open (deadline from today)."""
    from . import config
    from . import khmdhs as K

    res = K.scan(cpv_codes=cpv_codes, deadline_from=deadline_from or config.now_athens().strftime("%Y-%m-%d %H:%M"),
                 deadline_to=deadline_to, cost_from=cost_min, cost_to=cost_max, title=title)
    return {"total": res["total"], "criteria": res["criteria"], "notices": res["notices"][:limit]}


@mcp.tool()
def read_rules(notice_id: str) -> dict[str, Any]:
    """Read a tender's eligibility rules (turnover, similar projects, ISOs, team, guarantee, budget) from its own
    documents: the ΚΗΜΔΗΣ tender PDF when it can be found (TED number or ΑΔΑΜ), else the TED notice text.
    Every rule comes with an exact quote and page; the verifier re-opens that page and grades it. Returns the
    rules, where they were read from, and the receipts."""
    from datetime import datetime

    from . import config
    from . import rules as RL

    r = RL.read(notice_id)
    run_id = "rules_" + datetime.now(config.ATHENS).strftime("%Y%m%d_%H%M%S")
    receipts = V.verify(run_id, r["claims"]) if r["claims"] else []
    return {"notice_id": notice_id, "source": r["source"]["note"], "rules": r["rules"],
            "receipts": [{"claim": x["intent"]["claim_id"], "status": x["status"], "check": x["independent_check"]} for x in receipts]}


@mcp.tool()
def score_tenders(notices: list[dict], profile: dict | None = None, run_id: str | None = None) -> dict[str, Any]:
    """Rank notices with the visible TED-metadata fit formula (CPV, value vs turnover, place, days to deadline). Not eligibility."""
    return S.score_tenders(notices, profile or _demo_profile(), run_id=run_id)


@mcp.tool()
def check_eligibility(notice_id: str = "769674-2026", profile: dict | None = None, run_id: str | None = None) -> dict[str, Any]:
    """Check a company profile against the tender's rules with clause citations (section, PDF page, printed page),
    then have the independent verifier re-read each cited page. Returns the verdict and the receipts (VERIFIED/FAILED/UNVERIFIED).
    If profile is omitted, uses the demo 8-person Athens studio."""
    res = E.check_eligibility(notice_id, profile or _demo_profile(), run_id=run_id)
    res.pop("claims", None)
    return res


@mcp.tool()
def draft_cover_letter(notice_id: str, run_id: str, profile: dict | None = None) -> dict[str, Any]:
    """Draft the Greek consortium-partner letter for a run that already has an eligibility report."""
    report = E.load_report(run_id) or {}
    return L.draft_cover_letter(notice_id, profile or _demo_profile(), report, run_id=run_id)


@mcp.tool()
def verify(run_id: str) -> dict[str, Any]:
    """Re-run (idempotently) the independent checks for every claim stored on a run and report whether it is ready."""
    receipts = V.verify(run_id)
    return {"receipts": receipts, "state": V.run_state(run_id)}


@mcp.tool()
def build_pack(run_id: str, notice_id: str = "769674-2026") -> dict[str, Any]:
    """Build the handover ZIP (letter, checklist, receipts.json, deadline.ics). Never submits on ΕΣΗΔΗΣ; marked ready only if the verifier says so."""
    return P.build_pack(run_id, notice_id)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    mcp.run()  # stdio
