"""build_pack: the handover ZIP (ASCII names), for any tender whose eligibility has been checked. Then stop.

Contents: a checklist that starts with what the bidder has to do (dated), then the rules and the
verifier's checks; the tender document; a deadline .ics; the receipts; a README; and, where we have
one, the Greek consortium letter. A human signs and submits on ΕΣΗΔΗΣ. The pack is marked ready only
if the verifier says so.
"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, verifier
from . import receipts as R
from .eligibility import KTP, SHORT, load_report

ATHENS = ZoneInfo("Europe/Athens")
DEADLINE_LOCAL = "2026-12-07T14:00"  # ΚτΠ; verified against the RFP page in check_eligibility


# ---- tender facts (deadline, ΕΣΗΔΗΣ number, buyer, document) -------------------------------------

def tender_facts(notice_id: str) -> dict:
    """What the pack needs to know about the tender. ΚτΠ from its hand-made index; any other tender
    from TED plus its matched ΚΗΜΔΗΣ record. The deadline is re-checked by the verifier either way."""
    from . import khmdhs, ted
    from . import tender_source as T

    if notice_id == KTP:
        n = T.requirements(KTP)["notice"]
        return {"title": n["title"], "buyer": n["buyer"].split(",")[0], "esidis": "589064", "adam": "26PROC020137847",
                "deadline": DEADLINE_LOCAL, "deadline_checked_by": "deadline_on_page",
                "dates": [("2026-11-18", "Last day for clarification questions on ΕΣΗΔΗΣ")],
                "document": T.notice_dir(KTP) / T.rfp_file_rel()}
    n = (ted.get_notice(notice_id, run_id="pack").get("notice") or {})
    raw = n.get("deadline_raw") or {}
    mf = config.DATA_DIR / khmdhs.CACHE / "ted-matches.json"
    m = (json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}).get(notice_id) or {}
    rec = m.get("record") or {}
    doc = config.DATA_DIR / khmdhs.CACHE / rec["adam"] / "document.pdf" if rec.get("adam") else None
    deadline = verifier.athens_deadline(raw.get("date"), raw.get("time")) or ((rec.get("deadline") or "")[:16] or None)
    return {"title": rec.get("title") or n.get("title") or notice_id, "buyer": rec.get("buyer_name") or n.get("buyer_name"),
            "esidis": (rec.get("esidis") or [None])[0], "adam": rec.get("adam"), "deadline": deadline,
            "deadline_checked_by": "deadline_two_sources", "dates": [],
            "document": doc if doc and doc.exists() else None}


def _fmt(local: str) -> str:
    d = datetime.fromisoformat(local)
    return d.strftime("%a %d %b %Y, %H:%M").replace(" 0", " ") + " (Athens)"


def build_ics(path: Path, notice_id: str, deadline_local: str = DEADLINE_LOCAL, esidis: str | None = "589064") -> Path:
    start = datetime.fromisoformat(deadline_local).replace(tzinfo=ATHENS).astimezone(timezone.utc)
    z = lambda d: d.strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bid-Ready//Hackathon//EN", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:deadline-{notice_id}@bid-ready",
        f"DTSTAMP:{z(datetime.now(timezone.utc))}",
        f"DTSTART:{z(start)}",
        f"DTEND:{z(start + timedelta(hours=1))}",
        f"SUMMARY:Tender deadline TED {notice_id} ({deadline_local[11:]} Athens) - submit on ESIDIS" + (f" {esidis}" if esidis else ""),
        f"DESCRIPTION:Submission deadline {_fmt(deadline_local)}. https://ted.europa.eu/en/notice/-/detail/{notice_id}",
        "BEGIN:VALARM", "TRIGGER:-P2D", "ACTION:DISPLAY", "DESCRIPTION:Tender deadline in 2 days", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    return path


# ---- the checklist: to-do first, then rules, checks and quotes ------------------------------------

MARK = {"meets": "✓ meets", "missing": "✗ missing", "unclear": "? open"}


def _quote(s: str | None, n: int = 320) -> str:
    """Whole words only, with … where we cut."""
    s = re.sub(r"\s+", " ", s or "").strip()
    if not s:
        return ""
    if len(s) > n:
        s = s[:n].rsplit(" ", 1)[0] + " …"
    return s


def _page(c: dict | None) -> str:
    c = c or {}
    if c.get("pdf_page") is None:
        return c.get("section") or "-"
    pr = c.get("printed_page")
    return f"p{c['pdf_page']}" + (f", printed {pr}" if pr not in (None, c["pdf_page"]) else "")


def _sec(c: dict | None) -> str:
    s = (c or {}).get("section") or ""
    return f"§{s}" if re.match(r"\d", s) else s


def _day(d: str) -> str:
    return datetime.fromisoformat(d).strftime("%a %d %b %Y").replace(" 0", " ")


def _where(c: dict | None) -> str:
    return " ".join(x for x in (_sec(c), _page(c)) if x and x != "-")


def _check_line(r: dict, titles: dict) -> str:
    """One readable line per verifier receipt; rules read live carry JSON values, so name the rule instead."""
    claim = r["intent"].get("claim") or r["intent"].get("claim_id") or ""
    cid = r["intent"].get("claim_id") or ""
    if "{" in claim:
        rid = cid.split(":", 1)[-1]
        src = re.sub(r"^khmdhs-cache/\S+", "the tender document", (r.get("independent_check") or {}).get("source") or "the tender")
        claim = f"{titles.get(rid, rid)}: the quoted wording and values are on {src}"
    return claim


def todo(report: dict, facts: dict, state: dict, has_letter: bool) -> list[str]:
    """Numbered, in the order a bidder would do them."""
    items: list[str] = []
    rules = [r for r in report["rules"] if r.get("kind", "rule") == "rule"]
    verdict = report["verdict"]
    for d, what in facts["dates"]:
        items.append(f"**By {_day(d)}:** {what}, if anything in the rules below is unclear to you.")
    if verdict == "not_eligible":
        gaps = [SHORT.get(r["id"], r["title"]) for r in rules if r["status"] == "missing"]
        items.append("**Find a partner.** You can't bid alone. A partner would need to bring: " + "; ".join(gaps) + ".")
        if has_letter:
            items.append("**Send the consortium letter** (consortium_letter_el.docx) to possible partners, after filling in the [brackets].")
        if report["notice_id"] == KTP:
            items.append("**Agree the form with the partner:** a joint venture (turnover and profit are pooled, §2.2.5, but every member "
                         "needs the ISO certificates, §2.2.7), or subcontracting, where you only sign a declaration accepting the work "
                         "(§2.2.9.2 B.10, p48, printed 41).")
        else:
            items.append("**Agree the form with the partner** (joint venture or subcontracting). Check the tender's rules on both first.")
    for r in rules:
        if r["status"] == "unclear":
            q = (r.get("ask") or {}).get("question")
            items.append(f"**Answer: {r['title']}** ({_where(r.get('citation'))}). "
                         + (q or r.get("notes") or "") + " Then run the check again.")
    for r in rules:
        if r.get("declared") and r["status"] == "meets":
            items.append(f"**Gather proof for: {r['title']}.** You declared it yourself; the buyer will ask for evidence "
                         f"({_where(r.get('citation'))}).")
    provide = [p for p in report.get("provide") or [] if p.get("icon") != "calendar"]  # the deadline is the last step
    lead = "Whoever leads the bid will need: " if verdict == "not_eligible" else ""
    for p in provide:
        cite = p.get("citation")
        t = p["text"]
        text = (t[0].lower() + t[1:]) if lead and not t[:2].isupper() else t
        items.append(f"**{lead}{text}**" + (f" ({_where(cite)})" if cite else "") + ".")
    by_id = {r["id"]: r for r in report["rules"]}
    for f in state.get("failed") or []:
        r = by_id.get(f)
        items.append(f"**Why the pack says NOT READY:** {r['notes'] if r else f'the check {f} failed (see Checks).'} "
                     "The verifier keeps this check FAILED on purpose, so nobody hands over a wrong figure as done.")
    if facts.get("deadline"):
        items.append("**Add deadline.ics to your calendar** (reminder 2 days before).")
    who = "**The lead bidder reviews, signs and submits on ΕΣΗΔΗΣ**" if verdict == "not_eligible" else "**Review, sign and submit yourself on ΕΣΗΔΗΣ**"
    items.append(who + (f" (α/α {facts['esidis']})" if facts.get("esidis") else "")
                 + (f" by **{_fmt(facts['deadline'])}**" if facts.get("deadline") else "") + ". Bid-Ready does not submit.")
    return [f"{i}. {t}" for i, t in enumerate(items, 1)]


def build_checklist(path: Path, report: dict, receipts: list[dict], state: dict, facts: dict | None = None,
                    has_letter: bool = False) -> Path:
    facts = facts or tender_facts(report["notice_id"])
    summ = report.get("summary") or {}
    rules = [r for r in report["rules"] if r.get("kind", "rule") == "rule"]
    checks = [r for r in receipts if r.get("independent_check") and r["status"] in ("VERIFIED", "FAILED", "UNVERIFIED")
              and r.get("action") != "second_opinion"]
    n_ok = sum(r["status"] == "VERIFIED" for r in checks)
    out = [
        f"# Bid checklist - TED {report['notice_id']}",
        "",
        f"**{facts['title']}**  ",
        f"Buyer: {facts.get('buyer') or '-'}  ",
        f"ΕΣΗΔΗΣ α/α: {facts.get('esidis') or 'not found'}" + (f" · ΑΔΑΜ {facts['adam']}" if facts.get("adam") else "") + "  ",
        f"Deadline: **{_fmt(facts['deadline']) if facts.get('deadline') else 'not found: check the tender'}**",
        "",
        f"## {summ.get('headline') or report['verdict']}",
        "",
        summ.get("sub") or "",
        "",
        f"Pack: **{'READY' if state['ready'] else 'NOT READY'}**. "
        + (f"All {n_ok} checks agree with the tender." + ("" if report["verdict"] == "eligible" else " That is about the checks, not your eligibility: see the to-do.") if state["ready"] else
           f"{n_ok} of {len(checks)} checks agree with the tender; "
           + ", ".join(state["failed"] + state["unverified"]) + " did not (see Checks)."),
        "",
        "## To do",
        "",
        *todo(report, facts, state, has_letter),
        "",
        "## Rules",
        "",
        "| Rule | You | Status | Where in the tender |",
        "|---|---|---|---|",
    ]
    for r in rules:
        you = (r.get("you") or "-") + (" (self-declared)" if r.get("declared") else "")
        out.append(f"| {r['title']} | {you} | {MARK.get(r['status'], r['status'])} | {_where(r.get('citation'))} |")
    out += ["", "## Checks", "",
            "Each line is one thing Bid-Ready claimed and the verifier re-read in the tender (or in this pack).", ""]
    titles = {r["id"]: r["title"] for r in report["rules"]}
    for r in checks:
        line = f"- **{r['status']}** - {_check_line(r, titles)}"
        if r["status"] != "VERIFIED" and r.get("reason"):
            line += f"  \n  {r['reason']}"
        out.append(line)
    out += ["", "## What the tender says", ""]
    for r in report["rules"]:
        c = r.get("citation") or {}
        q = _quote(c.get("quoted_span"))
        out.append(f"- **{r['title']}** ({_where(c)}): {r.get('notes') or ''}")
        if q:
            out.append(f"  > {q}")
    if report.get("source_flags"):
        out += ["", "## Errors in the tender itself (flagged, not corrected)", ""] + [f"- {f}" for f in report["source_flags"]]
    out += ["", "---", "A human reviews, signs and submits on ΕΣΗΔΗΣ (promitheus.gov.gr). Bid-Ready stops here."]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def build_readme(path: Path, notice_id: str, facts: dict, state: dict, entries: dict) -> Path:
    what = {
        "eligibility_checklist.md": "Start here: what to do, by when; the rules; every check the verifier ran.",
        "consortium_letter_el.docx": "Greek letter to a possible partner (Word). Fill in the [brackets], then sign.",
        "consortium_letter_el.md": "The same letter as plain text.",
        "tender_document.pdf": "The tender document the rules and quotes were read from.",
        "deadline.ics": "The submission deadline for your calendar, Europe/Athens time.",
        "receipts.json": "Machine-readable record of every step and check.",
        "README.txt": "This file.",
    }
    lines = [f"Bid-Ready handover pack - TED {notice_id}",
             facts["title"], "",
             f"Status: {'READY' if state['ready'] else 'NOT READY'}"
             + ("" if state["ready"] else f" - these checks did not pass: {', '.join(state['failed'] + state['unverified'])}"),
             f"Deadline: {_fmt(facts['deadline']) if facts.get('deadline') else 'not found'}", "", "Files:"]
    lines += [f"  {name:<28} {what.get(name, '')}" for name in entries]
    lines += ["", "A human reviews, signs and submits on ESIDIS (promitheus.gov.gr). Bid-Ready does not submit."]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return path


# ---- build ---------------------------------------------------------------------------------------

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

    facts = tender_facts(notice_id)
    letter = d / "consortium_letter_el.md"
    has_letter = letter.exists()
    pack_claims = []
    if has_letter:
        pack_claims.append({"claim_id": "pack:letter", "kind": "file_readable", "origin": "build_pack",
                            "statement": "Greek consortium letter exists and is readable.",
                            "check": {"path": str(letter), "must_contain": "ΕΣΗΔΗΣ"}, "value": letter.name, "required": True})
    if facts["deadline_checked_by"] == "deadline_two_sources":
        pack_claims.append({"claim_id": "pack:deadline", "kind": "deadline_two_sources", "origin": "build_pack", "notice_id": notice_id,
                            "statement": f"Submission deadline is {_fmt(facts['deadline']) if facts['deadline'] else 'known'} (TED and ΚΗΜΔΗΣ agree).",
                            "check": {}, "value": facts["deadline"], "required": True})
    ics = None
    if facts["deadline"]:
        ics = build_ics(d / "deadline.ics", notice_id, facts["deadline"], facts.get("esidis"))
        pack_claims.append({"claim_id": "pack:ics", "kind": "ics_deadline", "origin": "build_pack",
                            "statement": f"deadline.ics is {_fmt(facts['deadline'])}.",
                            "check": {"path": str(ics)}, "value": facts["deadline"], "required": True})
    verifier.verify(run_id, pack_claims)

    receipts = R.list_receipts(run_id)
    state = verifier.run_state(run_id)
    entries: dict[str, Path] = {}
    entries["eligibility_checklist.md"] = d / "eligibility_checklist.md"
    if has_letter:
        docx = d / "consortium_letter_el.docx"
        if docx.exists():
            entries["consortium_letter_el.docx"] = docx
        entries["consortium_letter_el.md"] = letter
    if facts.get("document"):
        entries["tender_document.pdf"] = Path(facts["document"])
    if ics:
        entries["deadline.ics"] = ics
    entries["receipts.json"] = d / "receipts.json"
    entries["README.txt"] = d / "README.txt"

    build_checklist(entries["eligibility_checklist.md"], report, receipts, state, facts, has_letter)
    entries["receipts.json"].write_text(json.dumps({"run_id": run_id, "state": state, "receipts": receipts}, ensure_ascii=False, indent=1), encoding="utf-8")
    build_readme(entries["README.txt"], notice_id, facts, state, entries)

    zpath = d / f"bidready_pack_{notice_id}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in entries.items():
            assert arc.isascii(), arc
            z.write(src, arc)

    required = [n for n in ("consortium_letter_el.md", "eligibility_checklist.md", "receipts.json", "deadline.ics") if n in entries]
    zr = verifier.verify(run_id, [{
        "claim_id": "pack:zip", "kind": "zip_entries", "origin": "build_pack",
        "statement": "ZIP opens, entry names are ASCII, and " + ", ".join(required) + " are present.",
        "check": {"path": str(zpath), "required": required},
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
    return {"run_id": run_id, "built": True, "zip_path": str(zpath), "entries": list(entries), "ready": state["ready"],
            "state": state, "verdict": report["verdict"], "todo": todo(report, facts, state, has_letter), "zip_receipt": zr, "receipt": receipt}
