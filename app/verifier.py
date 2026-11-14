"""Verifier core: re-reads the cited tender page (or pack file) and grades each claim.

Domain-agnostic contract:
  claim -> independent observation from the SOURCE (not requirements.json) -> VERIFIED / FAILED / UNVERIFIED.
The agent's own word is never accepted. A run is 'ready' only if every required claim is VERIFIED.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Callable

from . import receipts as R
from . import tender_source as T

Check = Callable[[dict], dict]  # returns {"observed": ..., "mismatch": bool|None, "source": str, "method": str}


class SourceUnavailable(Exception):
    pass


def _page(claim: dict) -> tuple[str, int]:
    cit = claim["citation"]
    return claim["notice_id"], int(cit["pdf_page"])


def _open(notice_id: str, pdf_page: int) -> str:
    try:
        return T.page_text(notice_id, pdf_page)
    except (FileNotFoundError, IndexError, OSError) as e:
        raise SourceUnavailable(str(e)) from e


def _src(claim: dict) -> str:
    c = claim["citation"]
    return f"RFP PDF p{c['pdf_page']} §{c['section']} (printed page {c.get('printed_page')}) via text/pages.json"


# ---- check kinds ---------------------------------------------------------------------------

def check_quote_on_page(claim: dict) -> dict:
    """The quoted span really is on the cited PDF page, and the printed footer matches."""
    nid, pg = _page(claim)
    _open(nid, pg)
    span = claim["citation"].get("quoted_span") or ""
    found = bool(span) and T.span_on_page(nid, pg, span)
    footer = T.printed_footer(nid, pg)
    printed_ok = footer is None or footer == claim["citation"].get("printed_page")
    return {
        "method": "reread_tender_pdf_page",
        "source": _src(claim),
        "observed": {"span_found": found, "printed_footer": footer},
        "mismatch": not (found and printed_ok),
    }


def check_amount_after_anchor(claim: dict) -> dict:
    """Re-read the clause and take the first euro amount after the anchor (e.g. §2.2.2.1 guarantee)."""
    nid, pg = _open_claim_page(claim)
    amounts = T.amounts_after(nid, pg, claim["check"]["anchor"], window=claim["check"].get("window", 700))
    if not amounts:
        raise SourceUnavailable(f"no amount after anchor on p{pg}")
    observed = amounts[0]
    field = claim["check"]["field"]
    pct = re.search(r"(\d+(?:,\d+)?)\s*%", T.norm(T.page_text(nid, pg))[T.norm(T.page_text(nid, pg)).find(T.norm(claim["check"]["anchor"])):][:700])
    return {
        "method": "reread_tender_pdf_page",
        "source": _src(claim),
        "observed": {field: observed, "basis": f"{pct.group(1) if pct else '?'}% as written in §{claim['citation']['section']}", "quote": T.find_span(nid, pg, f"{_fmt_gr(observed)}", after=0, before=140)},
        "mismatch": abs(float(claim["value"]) - observed) > 0.5,
    }


def check_turnover_threshold(claim: dict) -> dict:
    """Threshold = percentage written in §2.2.5 x initial budget excl. VAT and option written in §1.3."""
    nid, pg = _open_claim_page(claim)
    t = T.norm(T.page_text(nid, pg))
    m = re.search(r"\((\d+)%\)\s*του προϋπολογισμού", t)
    excl_option = "μη συμπεριλαμβανομένου Φ.Π.Α. και δικαιώματος προαίρεσης" in t
    budget_pg = int(claim["check"]["budget_pdf_page"])
    bt = T.norm(_open(nid, budget_pg))
    b = re.search(r"ανέρχεται σε [^()]*\((\d{1,3}(?:\.\d{3})+,\d{2}) €\) πλέον ΦΠΑ", bt)
    if not m or not b:
        raise SourceUnavailable("could not relocate percentage or budget")
    pct, budget = int(m.group(1)), T.parse_eur(b.group(1))
    observed = pct / 100 * budget
    return {
        "method": "reread_tender_pdf_page",
        "source": f"{_src(claim)} + budget on PDF p{budget_pg} §1.3",
        "observed": {"turnover_3y_total_min_eur": observed, "pct": pct, "budget_excl_vat_and_option": budget, "excludes_option": excl_option},
        "mismatch": abs(float(claim["value"]) - observed) > 0.5 or not excl_option,
    }


def check_deadline_on_page(claim: dict) -> dict:
    nid, pg = _open_claim_page(claim)
    t = T.norm(T.page_text(nid, pg))
    m = re.search(r"ΥΠΟΒΟΛΗΣ\s+(\d{2})-(\d{2})-(\d{4}).{0,40}?ώρα\s+(\d{2}:\d{2})", t)
    if not m:
        raise SourceUnavailable("deadline not found on page")
    observed = f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}"
    return {
        "method": "reread_tender_pdf_page",
        "source": _src(claim),
        "observed": {"deadline_local_europe_athens": observed},
        "mismatch": observed != claim["value"],
    }


def check_file_readable(claim: dict) -> dict:
    p = Path(claim["check"]["path"])
    if not p.exists():
        return {"method": "reread_pack_file", "source": str(p), "observed": {"exists": False}, "mismatch": True}
    data = p.read_bytes()
    must = claim["check"].get("must_contain")
    ok = len(data) > 0 and (must is None or must.encode("utf-8") in data)
    return {"method": "reread_pack_file", "source": p.name, "observed": {"exists": True, "bytes": len(data), "contains": must if ok else None}, "mismatch": not ok}


def check_ics_deadline(claim: dict) -> dict:
    p = Path(claim["check"]["path"])
    if not p.exists():
        return {"method": "reread_pack_file", "source": str(p), "observed": {"exists": False}, "mismatch": True}
    txt = p.read_text(encoding="utf-8")
    m = re.search(r"^DTSTART(;TZID=([^:]+))?:(\d{8}T\d{6})(Z?)\s*$", txt, re.M)
    if not m:
        return {"method": "reread_pack_file", "source": p.name, "observed": {"dtstart": None}, "mismatch": True}
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    tzid, stamp, z = m.group(2), m.group(3), m.group(4)
    dt = datetime.strptime(stamp, "%Y%m%dT%H%M%S")
    if z:
        local = dt.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Athens"))
    elif tzid:
        local = dt.replace(tzinfo=ZoneInfo(tzid))
    else:
        return {"method": "reread_pack_file", "source": p.name, "observed": {"dtstart": stamp, "floating": True}, "mismatch": True}
    observed = local.strftime("%Y-%m-%dT%H:%M")
    return {"method": "reread_pack_file", "source": p.name, "observed": {"dtstart_europe_athens": observed, "raw": m.group(0).strip()}, "mismatch": observed != claim["value"]}


def check_zip_entries(claim: dict) -> dict:
    p = Path(claim["check"]["path"])
    if not p.exists():
        return {"method": "reread_pack_file", "source": str(p), "observed": {"exists": False}, "mismatch": True}
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        bad = z.testzip()
    non_ascii = [n for n in names if not n.isascii()]
    missing = [n for n in claim["check"]["required"] if n not in names]
    return {"method": "reread_pack_file", "source": p.name, "observed": {"entries": names, "non_ascii": non_ascii, "missing": missing, "corrupt": bad}, "mismatch": bool(non_ascii or missing or bad)}


def _open_claim_page(claim: dict) -> tuple[str, int]:
    nid, pg = _page(claim)
    _open(nid, pg)
    return nid, pg


def _fmt_gr(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


CHECKS: dict[str, Check] = {
    "quote_on_page": check_quote_on_page,
    "amount_after_anchor": check_amount_after_anchor,
    "turnover_threshold": check_turnover_threshold,
    "deadline_on_page": check_deadline_on_page,
    "file_readable": check_file_readable,
    "ics_deadline": check_ics_deadline,
    "zip_entries": check_zip_entries,
}


# ---- public API ----------------------------------------------------------------------------

def verify_claim(run_id: str, claim: dict) -> dict:
    key = f"verify:{run_id}:{claim['claim_id']}:v1"
    existing = R.get_by_key(key)
    if existing:
        return existing  # idempotent retry: first receipt wins, nothing re-done
    try:
        ic = CHECKS[claim["kind"]](claim)
        ic["checker"] = "verifier-core"
        status = "FAILED" if ic["mismatch"] else "VERIFIED"
        reason = claim.get("fail_reason") if status == "FAILED" else None
        if status == "FAILED" and not reason:
            reason = f"Observed {ic['observed']} does not match the claim."
    except SourceUnavailable as e:
        ic = {"checker": "verifier-core", "method": "reread", "source": str(claim.get("citation") or claim.get("check")), "observed": None, "mismatch": None, "error": str(e)}
        status, reason = "UNVERIFIED", f"Could not re-open the source: {e}. UNVERIFIED is not done."
    return R.write_receipt({
        "run_id": run_id,
        "idempotency_key": key,
        "actor": claim.get("actor", "bid-ready-agent"),
        "action": claim.get("origin", "verify"),
        "intent": {"claim": claim["statement"], "citation": claim.get("citation"), "claim_id": claim["claim_id"]},
        "tool_call": claim.get("tool_call", {"name": claim.get("origin", "verify")}),
        "tool_response": {"ok": True, "value": claim.get("value"), "basis": claim.get("basis")},
        "independent_check": ic,
        "status": status,
        "reason": reason,
    })


def verify(run_id: str, claims: list[dict] | None = None) -> list[dict]:
    if claims is None:
        claims = R.load_claims(run_id)
    else:
        R.save_claims(run_id, claims)
    return [verify_claim(run_id, c) for c in claims]


def run_state(run_id: str) -> dict[str, Any]:
    """'ready' only if every required claim has a VERIFIED receipt. Never on the agent's word."""
    claims = [c for c in R.load_claims(run_id) if c.get("required", True)]
    by_key = {r["idempotency_key"]: r for r in R.list_receipts(run_id)}
    pending, failed, unverified = [], [], []
    for c in claims:
        r = by_key.get(f"verify:{run_id}:{c['claim_id']}:v1")
        if r is None:
            pending.append(c["claim_id"])
        elif r["status"] == "FAILED":
            failed.append(c["claim_id"])
        elif r["status"] != "VERIFIED":
            unverified.append(c["claim_id"])
    if not claims or pending:
        state = "not_checked"
    elif failed or unverified:
        state = "not_ready"
    else:
        state = "ready"
    return {"run_id": run_id, "state": state, "ready": state == "ready", "pending": pending, "failed": failed, "unverified": unverified}
