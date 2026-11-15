"""The handover pack for a tender other than ΚτΠ: its own deadline (TED and ΚΗΜΔΗΣ must agree), no letter,
a to-do list first. Offline: the tender facts and the TED notice are stubbed."""
import re
import zipfile

from app import config, eligibility, letter, pack, ted, verifier
from app import receipts as R

NID = "774438-2026"
FACTS = {"title": "ΨΗΦΙΑΚΟ ΑΠΟΘΕΤΗΡΙΟ", "buyer": "ΔΗΜΟΣ ΓΟΡΤΥΝΑΣ", "esidis": "590225", "adam": "26PROC020136518",
         "deadline": "2026-12-14T15:00", "deadline_checked_by": "deadline_two_sources", "dates": [], "document": None}
REPORT = {
    "notice_id": NID, "verdict": "eligible", "ted_url": "", "partnership_note": None, "source_flags": [],
    "summary": {"headline": "You can bid on this one.", "sub": "You meet all 2 rules we found."},
    "rules": [
        {"id": "turnover", "kind": "rule", "title": "Turnover (yearly average) ≥ €125,101", "status": "meets", "you": "≈ €133,333 a year",
         "notes": "", "citation": {"section": "tender document", "pdf_page": 16, "printed_page": 16, "quoted_span": "μέσο γενικό ετήσιο κύκλο εργασιών"}},
        {"id": "team", "kind": "rule", "title": "Minimum project team", "status": "meets", "declared": True, "you": "3 of 3 roles",
         "notes": "", "citation": {"section": "tender document", "pdf_page": 16, "printed_page": 16}},
    ],
    "provide": [{"icon": "bank", "text": "Bank or insurer guarantee letter of €2,502",
                 "citation": {"section": "tender document", "pdf_page": 11, "printed_page": 11}},
                {"icon": "calendar", "text": "Submit on ΕΣΗΔΗΣ by Mon 14 Dec 2026, 15:00 (Athens)"}],
}


def _setup(monkeypatch, tmp_path, run_id, ted_time="15:00:00+02:00"):
    monkeypatch.setattr(pack, "tender_facts", lambda nid: dict(FACTS))
    monkeypatch.setattr(ted, "get_notice", lambda nid, run_id=None: {"notice": {"deadline_raw": {"date": "2026-12-14+02:00", "time": ted_time}}})
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")  # no ΚΗΜΔΗΣ match on disk: TED alone
    f = tmp_path / "seen.txt"
    f.write_text("ΕΣΗΔΗΣ", encoding="utf-8")
    claim = {"claim_id": "rule:turnover", "kind": "file_readable", "statement": "stand-in rule check",
             "check": {"path": str(f), "must_contain": "ΕΣΗΔΗΣ"}, "value": "x", "required": True}
    eligibility.save_claims(run_id, [claim])
    verifier.verify(run_id, [claim])
    eligibility._save_report(run_id, {**REPORT, "run_id": run_id})


def test_athens_deadline_from_ted_offsets():
    assert verifier.athens_deadline("2026-12-14+02:00", "15:00:00+02:00") == "2026-12-14T15:00"
    assert verifier.athens_deadline("2026-12-14", "13:00:00Z") == "2026-12-14T15:00"
    assert verifier.athens_deadline(None, "15:00") is None


def test_pack_for_another_tender(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, "p774")
    r = pack.build_pack("p774", NID)
    assert r["built"] and r["ready"], r["state"]
    names = zipfile.ZipFile(r["zip_path"]).namelist()
    assert "deadline.ics" in names and "consortium_letter_el.md" not in names and all(n.isascii() for n in names)
    ics = (config.OUT_DIR / "p774" / "deadline.ics").read_text(encoding="utf-8")
    assert "DTSTART:20261214T130000Z" in ics and "ESIDIS 590225" in ics
    md = (config.OUT_DIR / "p774" / "eligibility_checklist.md").read_text(encoding="utf-8")
    assert md.index("## To do") < md.index("## Rules") < md.index("## Checks")
    todo = "\n".join(r["todo"])
    assert "Gather proof for: Minimum project team" in todo and "€2,502" in todo
    assert re.search(r"submit yourself on ΕΣΗΔΗΣ\*\* \(α/α 590225\) by \*\*Mon 14 Dec 2026, 15:00", todo)
    assert "Find a partner" not in todo


def test_deadline_disagreement_blocks_ready(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, "p774b", ted_time="16:00:00+02:00")
    r = pack.build_pack("p774b", NID)
    assert not r["ready"] and "pack:deadline" in r["state"]["failed"]
    assert any("Why the pack says NOT READY" in t for t in r["todo"])


def test_ktp_letter_ignores_team_answers_for_another_tender(studio_profile):
    p = {**studio_profile, "declarations": {"team": ["r0", "r1"]}}
    rep = eligibility.check_eligibility("769674-2026", p, run_id="lt1")
    let = letter.draft_cover_letter("769674-2026", p, rep, run_id="lt1", polish=False)
    assert "Ομάδα Έργου της §2.2.6.2" not in let["markdown"]
