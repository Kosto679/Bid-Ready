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


# ---- field observers: the answer key, read off the tender pages at check time ----------------

def _budget(nid: str) -> tuple[float, str]:
    t = T.norm(_open(nid, 17))
    m = re.search(r"ανέρχεται σε [^()]*\((\d{1,3}(?:\.\d{3})+,\d{2}) €\) πλέον ΦΠΑ", t)
    if not m:
        raise SourceUnavailable("initial budget not found on p17")
    return T.parse_eur(m.group(1)), m.group(0)


def _obs_budget(nid: str) -> dict:
    v, q = _budget(nid)
    return {"value": v, "pages": [17], "quote": q}


def _obs_guarantee(nid: str) -> dict:
    amounts = T.amounts_after(nid, 27, "2.2.2.1", window=700)
    if not amounts:
        raise SourceUnavailable("guarantee not found on p27")
    return {"value": amounts[0], "pages": [27], "quote": T.find_span(nid, 27, "ποσοστό 2%", after=120)}


def _obs_turnover(nid: str) -> dict:
    t = T.norm(_open(nid, 33))
    m = re.search(r"\((\d+)%\)\s*του προϋπολογισμού", t)
    if not m:
        raise SourceUnavailable("turnover % not found on p33")
    b, _ = _budget(nid)
    return {"value": int(m.group(1)) / 100 * b, "pages": [33, 17], "quote": T.find_span(nid, 33, "διακόσια τοις εκατό (200%)", before=120, after=120)}


def _obs_perf_guarantee(nid: str) -> dict:
    t = T.norm(_open(nid, 72))
    m = re.search(r"ποσοστό (\d+)% επί της εκτιμώμενης αξίας της σύμβασης, μη συμπεριλαμβανομένου ΦΠΑ και χωρίς", t)
    if not m:
        raise SourceUnavailable("performance guarantee % not found on p72")
    b, _ = _budget(nid)
    return {"value": int(m.group(1)) / 100 * b, "pages": [72, 17], "quote": m.group(0)}


def _obs_date(nid: str, label: str) -> dict:
    t = T.norm(_open(nid, 11))
    m = re.search(label + r"\s+(\d{2})-(\d{2})-(\d{4}).{0,40}?ώρα\s+(\d{2}:\d{2})", t)
    if not m:
        raise SourceUnavailable(f"{label} not found on p11")
    return {"value": f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}", "pages": [11], "quote": m.group(0)}


def _obs_escrow_count(nid: str) -> dict:
    t = T.norm(_open(nid, 33))
    m = re.search(r"I\. Πέντε \((\d+)\) τουλάχ", t) or re.search(r"I\. \w+ \((\d+)\) τουλάχ", t)
    if not m:
        raise SourceUnavailable("escrow project count not found on p33")
    return {"value": int(m.group(1)), "pages": [33], "quote": m.group(0)}


def _obs_duration(nid: str) -> dict:
    t = T.norm(_open(nid, 17))
    m = re.search(r"διάρκεια της σύμβασης ορίζεται σε \w+ \((\d+)\) μήνες", t)
    if not m:
        raise SourceUnavailable("duration not found on p17")
    return {"value": int(m.group(1)), "pages": [17], "quote": m.group(0)}


def _obs_iso_count(nid: str) -> dict:
    t = T.norm(_open(nid, 36) + " " + _open(nid, 37))
    i, j = t.find("2.2.7"), t.find("2.2.8")
    sect = t[i:j if j > i else None]
    stds = sorted(set(re.findall(r"ISO(?:/IEC)?\s*(\d{4,5})", sect)))
    if not stds:
        raise SourceUnavailable("no ISO standards found in §2.2.7")
    return {"value": len(stds), "pages": [36, 37], "quote": ", ".join("ISO " + s for s in stds)}


OBSERVERS: dict[str, Callable[[str], dict]] = {
    "initial_budget_ex_vat_eur": _obs_budget,
    "participation_guarantee_eur": _obs_guarantee,
    "turnover_3y_min_eur": _obs_turnover,
    "performance_guarantee_eur": _obs_perf_guarantee,
    "submission_deadline": lambda nid: _obs_date(nid, "ΥΠΟΒΟΛΗΣ"),
    "technical_opening": lambda nid: _obs_date(nid, "ΑΠΟΣΦΡΑΓΙΣΗΣ ΠΡΟΣΦΟΡΩΝ"),
    "escrow_projects_required": _obs_escrow_count,
    "contract_duration_months": _obs_duration,
    "iso_certificates_required": _obs_iso_count,
}


def same_value(claimed, observed) -> bool:
    if claimed is None:
        return False
    if isinstance(observed, (int, float)):
        try:
            return abs(float(claimed) - float(observed)) <= 0.5
        except (TypeError, ValueError):
            return False
    return str(claimed).strip().replace(" ", "T")[:16] == str(observed)[:16]


def check_field_value(claim: dict) -> dict:
    nid, field = claim["notice_id"], claim["check"]["field"]
    obs = OBSERVERS[field](nid)
    return {
        "method": "reread_tender_pdf_page",
        "source": f"RFP PDF p{'+'.join(map(str, obs['pages']))} via text/pages.json",
        "observed": {field: obs["value"], "quote": obs["quote"]},
        "mismatch": not same_value(claim["value"], obs["value"]),
    }


# ---- checks without an answer key (tenders nobody annotated) ---------------------------------

def _value_forms(v: Any, kind: str) -> list[str]:
    """Ways a value can be written in Greek tender text."""
    if kind in ("num", "int"):
        n = float(v)
        whole = f"{n:,.0f}"
        return [whole.replace(",", "."), whole.replace(",", "") , whole, f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")]
    if kind == "datetime":
        y, mo, d, hm = v[0:4], v[5:7], v[8:10], v[11:16]
        return [f"{d}-{mo}-{y}", f"{d}/{mo}/{y}", f"{d}.{mo}.{y}", f"{int(d)}/{int(mo)}/{y}", hm]
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def check_quote_supports_value(claim: dict) -> dict:
    c = claim["check"]
    pg, quote, kind = c.get("pdf_page"), c.get("quote") or "", c.get("type", "num")
    if claim.get("value") is None:
        raise SourceUnavailable("the model gave no value")
    if not isinstance(pg, int):
        raise SourceUnavailable("the model gave no page")
    try:
        page = T.pack_page(c["pack"], pg)
    except (FileNotFoundError, IndexError) as e:
        raise SourceUnavailable(str(e)) from e
    on_page = bool(quote) and T.norm(quote) in T.norm(page)
    forms = _value_forms(claim["value"], kind)
    q = T.norm(quote)
    if kind == "datetime":
        supported = any(f in q for f in forms[:4]) and forms[4] in q
    elif kind == "list":
        supported = all(f in q for f in forms)
    else:
        supported = any(f in q for f in forms)
    return {
        "method": "reread_tender_pdf_page", "source": f"{c['pack']} PDF p{pg} via page text",
        "observed": {"quote_on_page": on_page, "value_in_quote": supported, "looked_for": forms[:3]},
        "mismatch": not (on_page and supported),
    }


def check_arithmetic_pct(claim: dict) -> dict:
    """value == (percentage written in the cited clause) x base. Re-reads the clause to get the %."""
    c = claim["check"]
    try:
        page = T.norm(T.pack_page(c["pack"], int(c["pdf_page"])))
    except (FileNotFoundError, IndexError, TypeError, ValueError) as e:
        raise SourceUnavailable(str(e)) from e
    quote = T.norm(c.get("quote") or "")
    if not quote or quote not in page:
        raise SourceUnavailable("the clause quote is not on the cited page")
    i = page.find(quote)
    window = page[max(0, i - 300): i + len(quote) + 300]
    m = re.search(r"(\d+(?:,\d+)?)\s*%", quote) or re.search(r"(\d+(?:,\d+)?)\s*%", window)
    if not m:
        raise SourceUnavailable("no percentage stated near the clause")
    pct = float(m.group(1).replace(",", "."))
    expected = pct / 100 * float(c["base"])
    return {
        "method": "reread_tender_pdf_page", "source": f"{c['pack']} PDF p{c['pdf_page']} via page text",
        "observed": {"percentage_on_page": pct, "base": c["base"], "expected": round(expected, 2)},
        "mismatch": abs(expected - float(claim["value"])) > 0.5,
    }


def _open_src(src: dict | None) -> str:
    if not src:
        raise SourceUnavailable("no source page/block")
    try:
        return T.open_ref(src)
    except (FileNotFoundError, IndexError, ValueError, KeyError) as e:
        raise SourceUnavailable(str(e)) from e


def _src_name(src: dict) -> str:
    return f"{src['pack']} PDF p{src['page']}" if src.get("kind") == "pack" else f"TED notice {src.get('pub')} block {src.get('block')}"


def check_rule_quote(claim: dict) -> dict:
    """Any source: the quote is in the re-opened page/block, and each `must` group has a form present in the quote."""
    c = claim["check"]
    text = T.norm(_open_src(c.get("source")))
    q = T.norm(c.get("quote") or "")
    on_page = bool(q) and q in text
    groups = c.get("must") or []
    found = [any(T.norm(f) in q for f in g) for g in groups]
    return {"method": "reread_source", "source": _src_name(c["source"]),
            "observed": {"quote_in_source": on_page, "values_in_quote": found},
            "mismatch": not (on_page and all(found))}


def check_rule_arith(claim: dict) -> dict:
    """amount == pct% x base, and the pct really appears in the cited clause."""
    c = claim["check"]
    pct_ok = None
    if c.get("pct_source"):
        text = T.norm(_open_src(c["pct_source"]))
        pct_ok = bool(re.search(rf"(?<![\d,]){re.escape(f'{c['pct']:g}'.replace('.', ','))}\s*%", text))
    expected = float(c["pct"]) / 100 * float(c["base"])
    return {"method": "recompute", "source": _src_name(c["pct_source"]) if c.get("pct_source") else "extracted figures",
            "observed": {"expected": round(expected, 2), "pct_on_page": pct_ok},
            "mismatch": abs(expected - float(claim["value"])) > 0.5 or pct_ok is False}


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
    "field_value": check_field_value,
    "quote_supports_value": check_quote_supports_value,
    "arithmetic_pct": check_arithmetic_pct,
    "rule_quote": check_rule_quote,
    "rule_arith": check_rule_arith,
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
