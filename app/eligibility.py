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
from . import rule_cache, verifier
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
    "team": ("team", 35, "Έμπειρου Προγραμματιστή Εφαρμογών (Senior Developer)"),  # the roles are listed on p35
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
        return check_eligibility_generic(notice_id, profile, run_id, run_verify)

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

    rules.append({
        "id": "team",
        "title": "Named project team of 7 (PM, 4 developers, security officer, DPO)",
        "status": "unclear",
        "citation": _citation(notice_id, req, "team"),
        "notes": "Minimum CVs, on pain of exclusion: a project manager with 12 years, an information-security officer with 20, "
                 "and a DPO with a law degree, among others. We didn't ask about your team.",
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

    apply_declarations(rules, profile)
    core = [r for r in rules if r["id"] in ("turnover", "experience_escrow", "experience_sla", "experience_transformation", "iso")]
    exclusion = [r for r in rules if r["id"] in ("profitability", "team") and r["status"] == "missing"]  # also on pain of exclusion
    if any(r["status"] == "missing" for r in core) or exclusion:
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
        rule_cache.save_from_receipts(notice_id, out["receipts"])
        _apply_guarantee_check(rules, out["receipts"])
    present(report, profile, out.get("receipts") or [], deadline="Monday 7 Dec 2026, 14:00 (Athens)")
    _second_opinion(report, profile)
    _save_report(run_id, report)  # the pack checklist reads this file
    out.update({k: report[k] for k in ("summary", "provide", "rules")})
    out["state"] = verifier.run_state(run_id)
    return out


# ---- presentation: one shape for every tender ---------------------------------------------------

SHORT = {
    "turnover": "enough turnover", "profitability": "profit in each year",
    "experience_escrow": "5 public escrow-payment projects", "experience_sla": "an SLA support project ≥ €200,000",
    "experience_transformation": "a digital-transformation project", "experience": "the required past projects",
    "iso": "the ISO certificates", "team": "the named team",
}
PROVIDE_IDS = {"participation_guarantee", "guarantee"}


def _you(rule_id: str, profile: dict) -> str:
    t = profile.get("turnover_2023_2025_total_eur")
    projects = profile.get("public_sector_projects_last_5y")
    if rule_id == "turnover":
        return f"€{t:,.0f} over 2023–25" if t is not None else "not given"
    if rule_id == "profitability":
        p = profile.get("profitable_last_3y")
        return "not given" if p is None else ("yes" if p else "no")
    if rule_id.startswith("experience"):
        if projects is None:
            return "not given"
        s = str(projects).strip()
        if re.fullmatch(r"(none|no|κανένα|-)\.?", s, re.I):
            return "none"
        if rule_id in ("experience_escrow", "experience_sla") and _count_escrow_projects(projects) == 0:
            return "no escrow-payment projects"
        return s if len(s) <= 60 else s[:57] + "…"
    if rule_id == "iso":
        certs = profile.get("certificates") or []
        return ", ".join(certs) if certs else "none"
    if rule_id == "team":
        size = profile.get("size")
        return f"{size} people, roles not given" if size else "team not given"
    return ""


# ---- self-declarations: rules only the company can answer (as it would in the ΕΕΕΣ) --------------

KTP_ROLES = [
    {"key": "pm", "label": "Project manager: 12+ years in public ICT, master's, led a Greek public payment system"},
    {"key": "senior_dev", "label": "2 senior developers: IT degree, 5+ years"},
    {"key": "dev", "label": "2 developers: 3+ years"},
    {"key": "infosec", "label": "Information-security officer: ISO 27001 auditor, 20+ years (10 in security), master's"},
    {"key": "dpo", "label": "Data-protection officer: law degree, master's, 10+ years (5 on GDPR)"},
]


def ask_for(rule: dict, generic: bool) -> dict | None:
    """The question a company can answer itself for this rule, or None."""
    rid = rule["id"]
    if rid == "profitability":
        return {"type": "yesno", "question": "Did you make a profit in each of 2023, 2024 and 2025?"}
    if rid == "experience_escrow":
        return {"type": "number", "question": "How many public-sector escrow-payment projects did you complete in 2021–2026?"}
    if rid == "experience_sla":
        return {"type": "yesno", "question": "Was one of them production support under an SLA worth €200,000 or more?"}
    if rid == "experience_transformation":
        return {"type": "yesno", "question": "Have you delivered a public digital-transformation consulting project that included maintenance?"}
    if rid == "experience" and generic:
        return {"type": "yesno", "question": f"Do you meet this? {rule.get('notes', '').replace('Required: ', '')}"}
    if rid == "team":
        roles = KTP_ROLES if not generic else [{"key": f"r{i}", "label": r} for i, r in enumerate(rule.get("roles") or [])]
        if roles:
            return {"type": "roles", "question": "Which of these people could you name in the bid (staff or contracted)?", "options": roles}
    return None


def apply_declarations(rules: list[dict], profile: dict, generic: bool = False) -> None:
    """Attach each rule's question, and let the company's own answers set its status (marked self-declared)."""
    decl = profile.get("declarations") or {}
    for r in rules:
        q = ask_for(r, generic)
        if not q:
            continue
        r["ask"] = {**q, "value": decl.get(r["id"])}
        if r["id"] not in decl:
            continue
        v = decl[r["id"]]
        if q["type"] == "yesno":
            ok = v in (True, "yes", "Yes", "true")
        elif q["type"] == "number":
            try:
                ok = int(v) >= 5
            except (TypeError, ValueError):
                continue
        else:  # roles
            have = set(v or [])
            missing = [o["label"].split(":")[0] for o in q["options"] if o["key"] not in have]
            ok = not missing
            if missing:
                r["notes"] = "You'd still need: " + "; ".join(missing) + "."
        r["status"] = "meets" if ok else "missing"
        r["declared"] = True
        r["you"] = ("declared " + (("yes" if ok else "no") if q["type"] == "yesno" else
                    f"{v} project{'s' if str(v) != '1' else ''}" if q["type"] == "number" else
                    f"{len(set(v or []))} of {len(q['options'])} roles"))


def present(report: dict, profile: dict, receipts: list[dict], deadline: str | None = None) -> None:
    """Adds rule["you"] and rule["kind"], report["summary"] (built only from the rule rows) and report["provide"]."""
    rows = report.get("rules") or []
    for r in rows:
        r["kind"] = "provide" if r["id"] in PROVIDE_IDS else "rule"
        if not r.get("declared"):
            r["you"] = _you(r["id"], profile)
            t = profile.get("turnover_2023_2025_total_eur")
            if r["id"] == "turnover" and t is not None and "average" in r.get("title", "").lower():
                r["you"] = f"≈ €{t / 3:,.0f} a year (€{t:,.0f} over 2023–25)"
    rules = [r for r in rows if r["kind"] == "rule"]
    missing = [r for r in rules if r["status"] == "missing"]
    verdict = report.get("verdict")
    subcontract = any(c.get("intent", {}).get("claim_id") == "cite:partnership:subcontractor_b10" and c.get("status") == "VERIFIED" for c in receipts)
    if verdict == "not_eligible":
        headline = "You can't bid on this alone." + (" You could join as a subcontractor." if subcontract else "")
        gaps = [SHORT.get(r["id"], r["title"]) for r in missing]
        sub = (f"{len(missing)} of {len(rules)} rules missing. A partner would need to bring "
               + (", ".join(gaps[:-1]) + " and " + gaps[-1] if len(gaps) > 1 else gaps[0]) + ".")
    elif verdict == "eligible":
        declared = [r for r in rules if r.get("declared")]
        headline = "You can bid on this one."
        sub = (f"You meet all {len(rules)} rules we found"
               + (f", {len(declared)} of them self-declared: the buyer will ask for evidence." if declared else ".")
               + " Arrange the guarantee and documents below.")
    elif not rules:
        headline, sub = "We couldn't read this tender's rules.", (report.get("source") or {}).get("note") or ""
    else:
        open_ = [r for r in rules if r["status"] == "unclear"]
        headline = "We can't tell yet."
        sub = (f"{len(open_)} rule{'s' if len(open_) != 1 else ''} need{'' if len(open_) != 1 else 's'} your answer: "
               + ", ".join(SHORT.get(r["id"], r["title"]).replace("the ", "", 1) if r["id"] in SHORT else r["title"] for r in open_)
               + ". Use “Answer” on those rows.")
    report["summary"] = {"headline": headline, "sub": sub, "missing": len(missing), "rules": len(rules),
                         "subcontract": subcontract and verdict == "not_eligible"}

    provide = []
    g = next((r for r in rows if r["id"] in PROVIDE_IDS), None)
    if g:
        amount = None
        rec = next((x for x in receipts if x.get("intent", {}).get("claim_id") in ("participation_guarantee", "rule:guarantee")), None)
        if rec and rec.get("status") == "FAILED":
            amount = ((rec.get("independent_check") or {}).get("observed") or {}).get("participation_guarantee_eur")
        if amount is None:
            m = re.search(r"€([\d,]+)", g.get("notes") or "")
            amount = float(m.group(1).replace(",", "")) if m else None
        extra = ", paper original to ΚτΠ before the bids are opened on 11 Dec (unless issued electronically)" if report.get("notice_id") == KTP else ""
        provide.append({"icon": "bank", "text": f"Bank or insurer guarantee letter{f' of €{amount:,.0f}' if amount else ''}{extra}",
                        "citation": g.get("citation")})
    provide.append({"icon": "file", "text": "ΕΕΕΣ (ESPD), technical offer and financial offer, digitally signed"})
    if deadline:
        provide.append({"icon": "calendar", "text": f"Submit on ΕΣΗΔΗΣ by {deadline}"})
    report["provide"] = provide


def _apply_guarantee_check(rules: list[dict], receipts: list[dict]) -> bool:
    """Carry the verifier's verdict on the guarantee back onto its row, so the table never shows the naive figure as pending."""
    rec = next((r for r in receipts if (r.get("intent") or {}).get("claim_id") == "participation_guarantee"), None)
    row = next((r for r in rules if r["id"] == "participation_guarantee"), None)
    if not rec or not row:
        return False
    claimed = (rec.get("tool_response") or {}).get("value")
    seen = ((rec.get("independent_check") or {}).get("observed") or {}).get("participation_guarantee_eur")
    row["check"] = rec["status"]
    if rec["status"] == "FAILED" and seen is not None:
        row["notes"] = (f"Verifier FAILED the extractor's €{claimed:,.0f}: §2.2.2.1 on PDF p27 says €{seen:,.0f} "
                        f"(2% of the budget excl. VAT and option). Use €{seen:,.0f}.")
    elif rec["status"] == "VERIFIED":
        row["notes"] = f"€{claimed:,.0f}, confirmed on the cited page."
    return True


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


def check_eligibility_generic(notice_id: str, profile: dict, run_id: str, run_verify: bool = True, reader=None) -> dict:
    """Any tender without a hand-made index: rules read live (rules.py), verified, compared with the profile."""
    from . import rules as RL

    read = RL.read(notice_id, reader=reader)
    rows = RL.compare(read["rules"], profile) if read["rules"] else []
    claim_cit = {c["claim_id"]: c["citation"] for c in read["claims"] if c.get("citation")}
    for r in rows:
        r["citation"] = claim_cit.get(f"rule:{r['id']}") or r["citation"]
    apply_declarations(rows, profile, generic=True)
    verdict = RL.verdict(rows) if rows else "unclear"
    gaps = [r["title"] for r in rows if r["status"] == "missing"]
    report = {
        "run_id": run_id, "notice_id": notice_id, "ted_url": ted.ted_url(notice_id), "verdict": verdict,
        "generic": True, "source": {"kind": read["source"]["kind"], "note": read["source"]["note"]},
        "partnership_note": ("Alone you are not eligible. A partner would need to cover: " + "; ".join(gaps) +
                             ". Check the tender's rules on joint bids and subcontracting before you approach one.") if verdict == "not_eligible" else None,
        "rules": rows, "source_flags": [],
    }
    save_claims(run_id, read["claims"])
    _save_report(run_id, report)
    status = "RECORDED" if read["claims"] else "UNVERIFIED"
    receipt = write_receipt({
        "run_id": run_id, "idempotency_key": f"check_eligibility:{run_id}:{notice_id}",
        "action": "check_eligibility", "intent": {"notice_id": notice_id, "profile": profile.get("name"), "mode": "generic"},
        "tool_call": {"name": "check_eligibility", "arguments": {"notice_id": notice_id}},
        "tool_response": {"verdict": verdict, "rules": {r["id"]: r["status"] for r in rows}, "source": read["source"]["kind"]},
        "status": status,
        "reason": read["source"]["note"] if status == "UNVERIFIED" else "Rules read live; claims handed to the verifier.",
    })
    out = {**report, "claims": read["claims"], "receipt": receipt}
    if run_verify and read["claims"]:
        out["receipts"] = verifier.verify(run_id)
        rule_cache.save_from_receipts(notice_id, out["receipts"], read["rules"])
    else:
        out["receipts"] = [receipt]
    present(report, profile, out["receipts"], deadline=_deadline_text(notice_id))
    _second_opinion(report, profile)
    _save_report(run_id, report)
    out.update({k: report[k] for k in ("summary", "provide", "rules")})
    out["state"] = verifier.run_state(run_id)
    return out


def _second_opinion(report: dict, profile: dict, asker=None) -> None:
    """Oumi Iris reads the meaning-based rules (past projects, team) against the profile, as a second model.
    Advisory: shown beside our reading with a receipt, never changes the verdict or the run state."""
    from . import oumi

    if asker is None and not oumi.configured()[0]:
        return
    rows = report.get("rules") or []
    try:
        ops = oumi.second_opinion(rows, profile, asker=asker)
    except Exception as e:  # a second opinion is optional; its absence is recorded, not hidden
        ops, err = {}, f"{type(e).__name__}: {e}"[:200]
    else:
        err = None
    for r in rows:
        if r["id"] in ops:
            r["second_opinion"] = ops[r["id"]]
    if not ops and not err:
        return
    run_id = report["run_id"]
    write_receipt({
        "run_id": run_id, "idempotency_key": f"second_opinion:{run_id}:{report['notice_id']}", "actor": "oumi",
        "action": "second_opinion",
        "intent": {"claim": "A second, independent model reads the meaning-based rules against the company's own description."},
        "tool_call": {"name": "oumi_iris", "arguments": {"model": oumi.model_name(), "rules": sorted(ops)}},
        "tool_response": ops or {"error": err},
        "independent_check": {"checker": "oumi:iris", "method": "noul_per_rule", "source": "profile + rule text",
                              "observed": ops, "mismatch": any(not o["agrees"] for o in ops.values())},
        "status": "RECORDED" if ops else "UNVERIFIED",
        "reason": ("Advisory only; it does not change the verdict." if ops else f"Second opinion unavailable: {err}"),
    })


def _deadline_text(notice_id: str) -> str | None:
    try:
        n = (ted.get_notice(notice_id, run_id="deadline").get("notice") or {})
        if n.get("deadline_date"):
            from datetime import date as _d
            d = _d.fromisoformat(n["deadline_date"])
            return f"{d.strftime('%a %d %b %Y').replace(' 0', ' ')}{', ' + n['deadline_time'] if n.get('deadline_time') else ''} (Athens)"
    except Exception:
        return None
    return None


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
