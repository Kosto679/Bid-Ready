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
                 limit: int = 10, run_id: str | None = None) -> dict[str, Any]:
    """Search TED for open Greek IT tenders (TED Search API v3, no key). Falls back to the local pack and marks the live hop UNVERIFIED."""
    return T.find_tenders(query, place, cpv, deadline_from, limit, run_id=run_id, include=["769674-2026"])


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
