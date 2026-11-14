"""build_pack: handover ZIP (ASCII names) with letter, checklist, receipts, deadline .ics. Then stop.

A human signs and submits on ΕΣΗΔΗΣ. The pack is marked ready only if the verifier says so.
"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import config, verifier
from . import receipts as R
from .eligibility import load_report

DEADLINE_LOCAL = "2026-12-07T14:00"
DEADLINE_UTC = "20261207T120000Z"  # 14:00 Europe/Athens (EET, UTC+2)


def build_ics(path: Path, notice_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bid-Ready//Hackathon//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:deadline-{notice_id}@bid-ready",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{DEADLINE_UTC}",
        "DTEND:20261207T130000Z",
        f"SUMMARY:Tender deadline TED {notice_id} (14:00 Athens) - submit on ESIDIS 589064",
        f"DESCRIPTION:Submission deadline 7 Dec 2026 14:00 Europe/Athens. https://ted.europa.eu/en/notice/-/detail/{notice_id}",
        "BEGIN:VALARM",
        "TRIGGER:-P2D",
        "ACTION:DISPLAY",
        "DESCRIPTION:Tender deadline in 2 days",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    return path


STATUS_MARK = {"meets": "[x] meets", "missing": "[ ] MISSING", "unclear": "[?] unclear"}


def build_checklist(path: Path, report: dict, receipts: list[dict], state: dict) -> Path:
    by_claim = {r["intent"].get("claim_id"): r for r in receipts if r["intent"].get("claim_id")}
    out = [
        f"# Eligibility checklist - TED {report['notice_id']}",
        "",
        f"Verdict: **{report['verdict'].upper().replace('_', ' ')}**",
        f"Pack status: **{'READY' if state['ready'] else 'NOT READY'}** (verifier state: {state['state']})",
        "",
    ]
    if report.get("partnership_note"):
        out += [f"> {report['partnership_note']}", ""]
    out += ["| Rule | Status | Clause | PDF p / printed p | Verifier |", "|---|---|---|---|---|"]
    for r in report["rules"]:
        c = r["citation"]
        rc = by_claim.get(f"cite:{r['id']}")
        out.append(f"| {r['title']} | {STATUS_MARK[r['status']]} | §{c['section']} | {c['pdf_page']} / {c['printed_page']} | {rc['status'] if rc else 'not checked'} |")
    out += ["", "## Notes", ""]
    for r in report["rules"]:
        out.append(f"- **{r['title']}**: {r['notes']}")
        if r["citation"].get("quoted_span"):
            out.append(f"  - Quote (PDF p{r['citation']['pdf_page']}): \"{r['citation']['quoted_span']}\"")
    out += ["", "## Verifier receipts", ""]
    for r in receipts:
        if r["action"] in ("check_eligibility", "build_pack") and r.get("independent_check"):
            out.append(f"- {r['status']}: {r['intent'].get('claim')}" + (f" -- {r['reason']}" if r["status"] != "VERIFIED" and r.get("reason") else ""))
    out += ["", "## Source errors flagged (not silently corrected)", ""] + [f"- {f}" for f in report.get("source_flags", [])]
    out += ["", "---", "A human reviews, signs, and submits on ΕΣΗΔΗΣ (promitheus.gov.gr, system 589064). Bid-Ready stops here."]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def build_pack(run_id: str, notice_id: str) -> dict:
    d = config.OUT_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    report = load_report(run_id)
    pre = verifier.run_state(run_id)
    if report is None or pre["state"] == "not_checked":
        r = R.write_receipt({
            "run_id": run_id, "idempotency_key": f"build_pack:{run_id}:refused",
            "action": "build_pack", "intent": {"notice_id": notice_id},
            "tool_call": {"name": "build_pack", "arguments": {"run_id": run_id, "notice_id": notice_id}},
            "tool_response": {"built": False}, "status": "UNVERIFIED",
            "reason": "Refused: eligibility and verify must run before a pack is built.",
        })
        return {"run_id": run_id, "built": False, "ready": False, "state": pre, "receipt": r}

    letter = d / "consortium_letter_el.md"
    ics = build_ics(d / "deadline.ics", notice_id)

    # Pack-file claims: the verifier re-reads what we wrote.
    pack_claims = [
        {"claim_id": "pack:letter", "kind": "file_readable", "origin": "build_pack", "statement": "Greek consortium letter exists and is readable.",
         "check": {"path": str(letter), "must_contain": "ΕΣΗΔΗΣ"}, "value": letter.name, "required": True},
        {"claim_id": "pack:ics", "kind": "ics_deadline", "origin": "build_pack", "statement": "deadline.ics is Mon 7 Dec 2026, 14:00 Europe/Athens.",
         "check": {"path": str(ics)}, "value": DEADLINE_LOCAL, "required": True},
    ]
    verifier.verify(run_id, pack_claims)

    receipts = R.list_receipts(run_id)
    state = verifier.run_state(run_id)
    checklist = build_checklist(d / "eligibility_checklist.md", report, receipts, state)
    rjson = d / "receipts.json"
    rjson.write_text(json.dumps({"run_id": run_id, "state": state, "receipts": receipts}, ensure_ascii=False, indent=1), encoding="utf-8")
    readme = d / "README.txt"
    readme.write_text(
        f"Bid-Ready handover pack - TED {notice_id}\r\n"
        f"Status: {'READY' if state['ready'] else 'NOT READY'} ({', '.join(state['failed'] + state['unverified']) or 'all checks verified'})\r\n"
        "A human reviews, signs and submits on ESIDIS (promitheus.gov.gr). Bid-Ready does not submit.\r\n",
        encoding="utf-8",
    )

    entries = {"consortium_letter_el.md": letter, "eligibility_checklist.md": checklist, "receipts.json": rjson, "deadline.ics": ics, "README.txt": readme}
    docx = d / "consortium_letter_el.docx"
    if docx.exists():
        entries["consortium_letter_el.docx"] = docx
    zpath = d / f"bidready_pack_{notice_id}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in entries.items():
            assert arc.isascii(), arc
            z.write(src, arc)

    zr = verifier.verify(run_id, [{
        "claim_id": "pack:zip", "kind": "zip_entries", "origin": "build_pack",
        "statement": "ZIP opens, entry names are ASCII, and letter/checklist/receipts/ics are present.",
        "check": {"path": str(zpath), "required": ["consortium_letter_el.md", "eligibility_checklist.md", "receipts.json", "deadline.ics"]},
        "value": zpath.name, "required": True,
    }])[0]
    state = verifier.run_state(run_id)
    receipt = R.write_receipt({
        "run_id": run_id,
        "idempotency_key": f"build_pack:{run_id}:{notice_id}",
        "action": "build_pack",
        "intent": {"notice_id": notice_id},
        "tool_call": {"name": "build_pack", "arguments": {"run_id": run_id, "notice_id": notice_id}},
        "tool_response": {"zip": str(zpath), "entries": list(entries), "ready": state["ready"]},
        "status": "RECORDED",
        "reason": "Pack built. " + ("Ready for human signature." if state["ready"] else f"NOT READY: {', '.join(state['failed'] + state['unverified'])}."),
    })
    return {"run_id": run_id, "built": True, "zip_path": str(zpath), "entries": list(entries), "ready": state["ready"], "state": state, "zip_receipt": zr, "receipt": receipt}
