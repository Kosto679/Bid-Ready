"""check_eligibility: compare the profile to the notice rules, with citations, then hand every claim
to the independent verifier.

requirements.json is used only as a clause INDEX (which rule, which section, which page). Every
quoted span is lifted from the real page text, and the verifier re-opens that page again.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import config, ted
from . import tender_source as T
from . import verifier
from .receipts import new_run_id, save_claims, write_receipt

KTP = "769674-2026"

REQUIRED_ISOS = [
    ("9001", "ISO 9001:2015"),
    ("20000", "ISO/IEC 20000-1:2018"),
    ("27001", "ISO 27001 (notice says '27001:2019', sic)"),
    ("27701", "ISO 27701 (notice says '27701:2019', sic)"),
    ("22301", "ISO 22301:2019"),
    ("37001", "ISO 37001:2016"),
]

# rule id -> (index id in requirements.json, pdf page, anchor text that must be on that page)
ANCHORS = {
    "turnover": ("turnover", 33, "διακόσια τοις εκατό (200%)"),
    "profitability": ("profitability", 33, "Να εμφανίζουν κερδοφορία"),
    "experience_escrow": ("experience_escrow", 33, "συστημάτων υποστήριξης πληρωμών μέσω escrow accounts"),
    "experience_sla": ("experience_sla", 34, "Service Level Agreement"),
    "experience_transformation": ("experience_transformation", 34, "ψηφιακό μετασχηματισμό"),
    "iso": ("iso", 36, "ISO 9001:2015"),
    "participation_guarantee": ("participation_guarantee", 27, "2.2.2.1"),
}


def _index_cite(req: dict, index_id: str, pdf_page: int) -> dict:
    items = req["selection_criteria"] + req["documents"]
    item = next(i for i in items if i["id"] == index_id)
    cite = next((c for c in item["cite"] if c.get("pdf_page") == pdf_page), item["cite"][0])
    return cite


def _citation(notice_id: str, req: dict, rule: str) -> dict:
    index_id, pdf_page, anchor = ANCHORS[rule]
    cite = _index_cite(req, index_id, pdf_page)
    span = T.find_span(notice_id, pdf_page, anchor, after=180, before=60)
    return {
        "section": re.sub(r"\s.*$", "", cite["section"]) if cite["section"][0].isdigit() else cite["section"],
        "pdf_page": pdf_page,
        "printed_page": T.printed_page(pdf_page),
        "index_doc_page": cite.get("doc_page"),
        "quoted_span": span,
        "file": T.rfp_file_rel(),
    }


def _norm_certs(certs: list[str]) -> set[str]:
    found = set()
    for c in certs or []:
        for key, _ in REQUIRED_ISOS:
            if key in re.sub(r"\s", "", c):
                found.add(key)
    return found


def _projects_text(p: Any) -> str:
    if p is None:
        return ""
    return " ".join(map(str, p)) if isinstance(p, list) else str(p)


def _count_escrow_projects(projects: Any) -> int:
    if isinstance(projects, list):
        return sum(1 for x in projects if "escrow" in str(x).lower() and "no escrow" not in str(x).lower())
    s = _projects_text(projects).lower()
    if "no escrow" in s or "not escrow" in s or "χωρίς escrow" in s:
        return 0
    return s.count("escrow")


def naive_guarantee_from_ted(notice: dict) -> dict:
    """The naive extractor: trusts the TED procedure-level value. This is the mistake that headline invites."""
    value = notice.get("estimated_value")
    return {
        "participation_guarantee_eur": round(0.02 * value, 2) if value else None,
        "basis": f"2% of TED procedure-level value EUR {value:,.0f}" if value else "TED value missing",
    }


def check_eligibility(notice_id: str, profile: dict, run_id: str | None = None, run_verify: bool = True) -> dict:
    run_id = run_id or new_run_id()
    if notice_id != KTP or not T.has_local_pack(notice_id):
        receipt = write_receipt({
            "run_id": run_id, "idempotency_key": f"check_eligibility:{run_id}:{notice_id}",
            "action": "check_eligibility", "intent": {"notice_id": notice_id},
            "tool_call": {"name": "check_eligibility", "arguments": {"notice_id": notice_id}},
            "tool_response": {"verdict": "unclear"}, "status": "UNVERIFIED",
            "reason": "No local tender pack / clause index for this notice yet; cannot cite clauses.",
        })
        return {"run_id": run_id, "notice_id": notice_id, "verdict": "unclear", "rules": [], "claims": [], "receipts": [receipt], "state": verifier.run_state(run_id)}

    req = T.requirements(notice_id)
    value = req["notice"]["value"]
    initial = float(value["initial_ex_vat"])
    rules: list[dict] = []

    # Turnover: 3-year TOTAL >= 200% of the initial budget excl. VAT and option.
    threshold = 2.0 * initial
    tv = profile.get("turnover_2023_2025_total_eur")
    rules.append({
        "id": "turnover",
        "title": "Turnover 2023+2024+2025 (total)",
        "status": "unclear" if tv is None else ("meets" if tv >= threshold else "missing"),
        "citation": _citation(notice_id, req, "turnover"),
        "notes": (f"Needs a 3-year total ≥ €{threshold:,.0f} (200% of €{initial:,.0f} excl. VAT and option). "
                  + ("Turnover not given." if tv is None else f"You reported €{tv:,.0f}.")),
    })

    prof = profile.get("profitable_last_3y")
    rules.append({
        "id": "profitability",
        "title": "Profitable in each of 2023–2025",
        "status": "unclear" if prof is None else ("meets" if prof else "missing"),
        "citation": _citation(notice_id, req, "profitability"),
        "notes": "Self-declared; the buyer checks financial statements.",
    })

    projects = profile.get("public_sector_projects_last_5y")
    answered = projects is not None
    n_escrow = _count_escrow_projects(projects)
    rules.append({
        "id": "experience_escrow",
        "title": "≥5 public-sector escrow-payment system projects (2021–2026)",
        "status": "unclear" if not answered else ("meets" if n_escrow >= 5 else "missing"),
        "citation": _citation(notice_id, req, "experience_escrow"),
        "notes": ("Projects question skipped, so we cannot say." if not answered
                  else f"Found {n_escrow} escrow-payment projects in your answer; the notice needs at least 5, each with citizen ID via ΓΓΠΣΨΔ, bank interoperability, MIS and transaction documents."),
    })
    rules.append({
        "id": "experience_sla",
        "title": "≥1 of those with SLA production support ≥ €200,000",
        "status": "unclear" if not answered else ("unclear" if n_escrow >= 5 else "missing"),
        "citation": _citation(notice_id, req, "experience_sla"),
        "notes": "Must be one of the escrow projects, budget ≥ 100% of €200,000 excl. VAT.",
    })
    trans = answered and bool(re.search(r"transformation|μετασχηματ", _projects_text(projects), re.I))
    rules.append({
        "id": "experience_transformation",
        "title": "≥1 public digital-transformation consulting project incl. maintenance",
        "status": "unclear" if not answered else ("unclear" if trans else "missing"),
        "citation": _citation(notice_id, req, "experience_transformation"),
        "notes": "Consulting + technology services for digital transformation of processes, with maintenance/support.",
    })

    held = _norm_certs(profile.get("certificates") or [])
    missing_isos = [label for key, label in REQUIRED_ISOS if key not in held]
    rules.append({
        "id": "iso",
        "title": "Six ISO certificates (every JV member)",
        "status": "meets" if not missing_isos else "missing",
        "citation": _citation(notice_id, req, "iso"),
        "notes": ("Missing: " + "; ".join(missing_isos) + ". " if missing_isos else "") +
                 "Source flag: the notice cites editions '27001:2019' and '27701:2019', which do not exist — not silently corrected.",
    })

    # Participation guarantee: the naive path trusts TED's procedure-level value.
    notice_res = ted.get_notice(notice_id, run_id=run_id)
    notice = notice_res["notice"] or {"estimated_value": value["total_with_option_ex_vat"], "publication_number": notice_id}
    naive = naive_guarantee_from_ted(notice)
    g_cite = _citation(notice_id, req, "participation_guarantee")
    rules.append({
        "id": "participation_guarantee",
        "title": "Participation guarantee (bank letter, paper original before opening)",
        "status": "unclear",
        "citation": g_cite,
        "notes": f"Extractor computed €{naive['participation_guarantee_eur']:,.0f} ({naive['basis']}). Pending independent verification against §2.2.2.1.",
        "extracted": naive,
    })

    core = [r for r in rules if r["id"] in ("turnover", "experience_escrow", "experience_sla", "experience_transformation", "iso")]
    if any(r["status"] == "missing" for r in core):
        verdict = "not_eligible"
    elif any(r["status"] == "unclear" for r in core):
        verdict = "unclear"
    else:
        verdict = "eligible"

    partnership_note = (
        "Alone you are not eligible. A joint venture would need a partner with ≥5 public escrow-payment projects (one with SLA support ≥ €200,000) "
        "and a digital-transformation project. In a joint venture turnover and profitability are covered jointly (§2.2.5), but the ISO "
        "conditions are covered by each member (§2.2.7). As a subcontractor whose capacity the bidder does not rely on, you would only need "
        "a declaration accepting the work (§2.2.9.2 B.10, PDF p48 / printed 41)."
        if verdict == "not_eligible" else None
    )

    claims = _build_claims(run_id, notice_id, rules, naive, initial, req)
    if partnership_note:
        claims += _partnership_claims(notice_id)
    report = {
        "run_id": run_id,
        "notice_id": notice_id,
        "ted_url": ted.ted_url(notice_id),
        "verdict": verdict,
        "partnership_note": partnership_note,
        "rules": rules,
        "source_flags": [t["text"] for t in req["traps"] if t["id"] == "source_errors"],
    }
    save_claims(run_id, claims)
    _save_report(run_id, report)

    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"check_eligibility:{run_id}:{notice_id}",
        "action": "check_eligibility",
        "intent": {"notice_id": notice_id, "profile": profile.get("name")},
        "tool_call": {"name": "check_eligibility", "arguments": {"notice_id": notice_id}},
        "tool_response": {"verdict": verdict, "rules": {r["id"]: r["status"] for r in rules}, "claims": len(claims)},
        "status": "RECORDED",
        "reason": "Eligibility drafted; claims handed to the verifier. Not done until verify has run.",
    })
    out = {**report, "claims": claims, "receipt": receipt}
    if run_verify:
        out["receipts"] = verifier.verify(run_id)
    out["state"] = verifier.run_state(run_id)
    return out


def _build_claims(run_id: str, notice_id: str, rules: list[dict], naive: dict, initial: float, req: dict) -> list[dict]:
    claims = []
    for r in rules:
        claims.append({
            "claim_id": f"cite:{r['id']}",
            "notice_id": notice_id,
            "kind": "quote_on_page",
            "origin": "check_eligibility",
            "statement": f"Rule '{r['title']}' is stated at §{r['citation']['section']}, PDF p{r['citation']['pdf_page']} / printed {r['citation']['printed_page']}.",
            "citation": r["citation"],
            "value": r["citation"]["quoted_span"],
            "required": True,
        })
    g = next(r for r in rules if r["id"] == "participation_guarantee")
    claims.append({
        "claim_id": "participation_guarantee",
        "notice_id": notice_id,
        "kind": "amount_after_anchor",
        "origin": "check_eligibility",
        "statement": f"Participation guarantee is EUR {naive['participation_guarantee_eur']:,.0f} ({naive['basis']}).",
        "citation": {**g["citation"], "locator": f"§2.2.2.1, PDF p{g['citation']['pdf_page']} / printed {g['citation']['printed_page']}", "url": ted.ted_url(notice_id)},
        "check": {"anchor": "2.2.2.1", "field": "participation_guarantee_eur", "window": 700},
        "value": naive["participation_guarantee_eur"],
        "basis": naive["basis"],
        "tool_call": {"name": "extract_criteria", "arguments": {"notice_id": notice_id, "rule": "participation_guarantee"}},
        "fail_reason": ("A naive extractor trusted TED's headline value. The notice sets the guarantee on the initial budget "
                        "excl. VAT and option, so the cited page says otherwise. No 'done'."),
        "required": True,
    })
    t = next(r for r in rules if r["id"] == "turnover")
    claims.append({
        "claim_id": "turnover_threshold",
        "notice_id": notice_id,
        "kind": "turnover_threshold",
        "origin": "check_eligibility",
        "statement": f"Turnover rule: 2023+2024+2025 total ≥ EUR {2 * initial:,.0f} (200% of EUR {initial:,.0f} excl. VAT and option).",
        "citation": t["citation"],
        "check": {"budget_pdf_page": 17},
        "value": 2 * initial,
        "basis": "200% x initial budget excl. VAT and option",
        "required": True,
    })
    claims.append({
        "claim_id": "deadline",
        "notice_id": notice_id,
        "kind": "deadline_on_page",
        "origin": "check_eligibility",
        "statement": "Submission deadline is Mon 7 Dec 2026, 14:00 Europe/Athens.",
        "citation": {"section": "Συνοπτικά στοιχεία", "pdf_page": 11, "printed_page": T.printed_page(11), "file": T.rfp_file_rel()},
        "value": "2026-12-07T14:00",
        "required": True,
    })
    return claims


PARTNERSHIP_CITES = [
    ("pooled", "2.2.5", 33, "οι παραπάνω απαιτήσεις καλύπτονται αθροιστικά από τα μέλη της ένωσης",
     "In a joint venture, turnover and profitability are covered jointly by the members (§2.2.5)."),
    ("iso_per_member", "2.2.7", 36,"μπορεί να καλύπτονται από κάθε μέλος της ένωσης / κοινοπραξίας χωριστά",
     "In a joint venture, the §2.2.7 conditions are covered by each member separately."),
    ("subcontractor_b10", "2.2.9.2 B.10", 48, "χρήση υπεργολάβων, στις ικανότητες των οποίων δεν στηρίζεται",
     "A subcontractor whose capacity the bidder does not rely on needs a declaration accepting the work (B.10)."),
]


def _partnership_claims(notice_id: str) -> list[dict]:
    out = []
    for cid, section, pg, anchor, statement in PARTNERSHIP_CITES:
        out.append({
            "claim_id": f"cite:partnership:{cid}",
            "notice_id": notice_id,
            "kind": "quote_on_page",
            "origin": "check_eligibility",
            "statement": statement,
            "citation": {"section": section, "pdf_page": pg, "printed_page": T.printed_page(pg),
                         "quoted_span": T.find_span(notice_id, pg, anchor, before=40, after=120), "file": T.rfp_file_rel()},
            "value": anchor,
            "required": True,
        })
    return out


def _save_report(run_id: str, report: dict) -> None:
    d = config.OUT_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "eligibility.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


def load_report(run_id: str) -> dict | None:
    p = config.OUT_DIR / run_id / "eligibility.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
