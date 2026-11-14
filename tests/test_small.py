"""Small tests: page offset, .ics timezone, ZIP ASCII, guarantee maths, scoring formula, receipts."""
import re
import zipfile
from datetime import date

from app import pack, scoring, verifier
from app import receipts as R
from app import tender_source as T

KTP = "769674-2026"


# --- page offset ---------------------------------------------------------------------------
def test_page_offset_helper():
    assert T.printed_page(33) == 26
    assert T.printed_page(27) == 20


def test_page_offset_matches_index_and_real_footer():
    req = T.requirements(KTP)
    turnover = next(c for c in req["selection_criteria"] if c["id"] == "turnover")["cite"][0]
    assert (turnover["pdf_page"], turnover["doc_page"]) == (33, 26)
    guar = next(d for d in req["documents"] if d["id"] == "participation_guarantee")["cite"][0]
    assert (guar["pdf_page"], guar["doc_page"]) == (27, 20)
    # and the actual page text agrees ("26 - 103" footer)
    assert T.printed_footer(KTP, 33) == 26
    assert T.printed_footer(KTP, 27) == 20


# --- ics timezone --------------------------------------------------------------------------
def test_ics_not_floating(tmp_path):
    ics = pack.build_ics(tmp_path / "deadline.ics", KTP).read_text(encoding="utf-8")
    starts = re.findall(r"^DTSTART.*$", ics, re.M)
    assert starts and all(s.endswith("Z") or "TZID=" in s for s in starts)
    assert "DTSTART:20261207T120000Z" in ics or "DTSTART;TZID=Europe/Athens:20261207T140000" in ics


# --- zip ascii ------------------------------------------------------------------------------
def test_zip_ascii_rejects_greek(tmp_path):
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as z:
        z.writestr("deadline.ics", "x")
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("επιστολή.md", "x")
    claim = {"claim_id": "z", "kind": "zip_entries", "statement": "zip ok", "check": {"path": str(good), "required": ["deadline.ics"]}, "value": "good.zip"}
    assert verifier.verify("run_zip", [claim])[0]["status"] == "VERIFIED"
    claim2 = {**claim, "claim_id": "z2", "check": {"path": str(bad), "required": []}}
    r = verifier.verify("run_zip", [claim2])[0]
    assert r["status"] == "FAILED" and r["independent_check"]["observed"]["non_ascii"]


# --- guarantee maths -----------------------------------------------------------------------
def test_guarantee_calc():
    assert 0.02 * 200_000 == 4_000
    assert 0.02 * 300_000 == 6_000
    assert 0.04 * 200_000 == 8_000


def test_verifier_fails_6000_vs_page_4000():
    claim = {
        "claim_id": "g", "notice_id": KTP, "kind": "amount_after_anchor", "statement": "guarantee 6000",
        "citation": {"section": "2.2.2.1", "pdf_page": 27, "printed_page": 20},
        "check": {"anchor": "2.2.2.1", "field": "participation_guarantee_eur"}, "value": 6000,
    }
    r = verifier.verify("run_g", [claim])[0]
    assert r["status"] == "FAILED"
    assert r["independent_check"]["observed"]["participation_guarantee_eur"] == 4000
    ok = verifier.verify("run_g", [{**claim, "claim_id": "g2", "value": 4000}])[0]
    assert ok["status"] == "VERIFIED"


def test_unreadable_page_is_unverified():
    claim = {"claim_id": "u", "notice_id": KTP, "kind": "quote_on_page", "statement": "x",
             "citation": {"section": "x", "pdf_page": 999, "printed_page": 992, "quoted_span": "x"}}
    assert verifier.verify("run_u", [claim])[0]["status"] == "UNVERIFIED"


# --- receipts -------------------------------------------------------------------------------
def test_write_receipt_idempotent():
    a = R.write_receipt({"run_id": "r", "idempotency_key": "k1", "action": "x", "status": "RECORDED"})
    b = R.write_receipt({"run_id": "r", "idempotency_key": "k1", "action": "y", "status": "FAILED"})
    assert a == b and len(R.list_receipts("r")) == 1
    assert re.search(r"[+-]\d{2}:\d{2}$", a["ts"])  # ISO 8601 with offset


# --- scoring --------------------------------------------------------------------------------
def test_scoring_formula_ktp(studio_profile):
    notice = {"publication_number": KTP, "classification_cpv": ["72000000"], "estimated_value": 300000.0,
              "place_of_performance": ["EL304", "GRC"], "deadline_date": "2026-12-07"}
    s = scoring.score_one(notice, studio_profile, date(2026, 11, 15))
    # cpv 1, value 350k/600k, place 1, deadline 22/45
    expected = round(100 * (0.25 * 1 + 0.25 * (350000 / 600000) + 0.25 * 1 + 0.25 * (22 / 45)))
    assert s["fit_score"] == expected
    assert s["reason"].count(".") >= 1 and "€300,000" in s["reason"] and "22 days" in s["reason"]


def test_scoring_no_turnover_no_cpv():
    s = scoring.score_one({"publication_number": "x", "classification_cpv": ["45000000"], "estimated_value": 1e6,
                           "place_of_performance": ["FR101"], "deadline_date": "2026-11-10"}, {"cpv_codes": []}, date(2026, 11, 15))
    assert s["fit_score"] == 0
