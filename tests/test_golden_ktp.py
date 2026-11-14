"""Golden end-to-end on TED 769674-2026, fully offline (docs/07-tests.md)."""
import re
import zipfile
from pathlib import Path

from app import eligibility, letter, pack, verifier
from app import receipts as R

KTP = "769674-2026"


def test_golden_ktp(studio_profile):
    elig = eligibility.check_eligibility(KTP, studio_profile)
    run_id = elig["run_id"]
    rules = {r["id"]: r for r in elig["rules"]}

    # 1. honest verdict
    assert elig["verdict"] == "not_eligible"
    assert elig["partnership_note"]

    # 2. experience is MISSING (projects question answered), cites §2.2.6.1 with both page numbers
    exp = rules["experience_escrow"]
    assert exp["status"] == "missing"
    assert exp["citation"]["section"].startswith("2.2.6.1")
    assert exp["citation"]["pdf_page"] == 33 and exp["citation"]["printed_page"] == 26

    # 3. ISO missing, §2.2.7
    assert rules["iso"]["status"] == "missing"
    assert rules["iso"]["citation"]["section"].startswith("2.2.7")

    # turnover under €400k total -> missing
    assert rules["turnover"]["status"] == "missing"

    # 4. naive TED-headline path produces €6,000
    g_claim = next(c for c in elig["claims"] if c["claim_id"] == "participation_guarantee")
    assert g_claim["value"] == 6000
    assert "300,000" in g_claim["basis"]

    # 5. verify -> FAILED with €4,000 observed from the tender page, not from requirements.json
    receipts = verifier.verify(run_id)
    g = next(r for r in receipts if r["intent"]["claim_id"] == "participation_guarantee")
    assert g["status"] == "FAILED"
    assert g["independent_check"]["observed"]["participation_guarantee_eur"] == 4000
    assert g["independent_check"]["method"] == "reread_tender_pdf_page"
    src = g["independent_check"]["source"]
    assert "p27" in src and "2.2.2.1" in src and "printed page 20" in src
    assert "requirements.json" not in src

    # 6. not ready
    assert verifier.run_state(run_id)["ready"] is False

    # 7. Greek letter on disk
    let = letter.draft_cover_letter(KTP, studio_profile, elig, run_id=run_id)
    text = Path(let["path"]).read_text(encoding="utf-8")
    assert re.search(r"[α-ωΑ-Ω]{20,}", text.replace(" ", "")) and "ΕΣΗΔΗΣ" in text
    assert "4.000 €" in text and "6.000" not in text  # letter uses the verified figure

    # 8. ZIP: ASCII names, required entries
    res = pack.build_pack(run_id, KTP)
    assert res["built"] and res["ready"] is False
    with zipfile.ZipFile(res["zip_path"]) as z:
        names = z.namelist()
        for n in names:
            n.encode("ascii")
        for need in ("consortium_letter_el.md", "eligibility_checklist.md", "receipts.json", "deadline.ics"):
            assert need in names
        ics = z.read("deadline.ics").decode()
        assert "NOT READY" in z.read("README.txt").decode()

    # 9. .ics = Mon 7 Dec 2026 14:00 Athens
    assert "DTSTART:20261207T120000Z" in ics or "DTSTART;TZID=Europe/Athens:20261207T140000" in ics

    # pack-file receipts were re-read by the verifier
    statuses = {r["intent"].get("claim_id"): r["status"] for r in R.list_receipts(run_id)}
    assert statuses["pack:letter"] == "VERIFIED"
    assert statuses["pack:ics"] == "VERIFIED"
    assert statuses["pack:zip"] == "VERIFIED"


def test_projects_skipped_is_unclear(studio_profile):
    p = {**studio_profile, "public_sector_projects_last_5y": None}
    elig = eligibility.check_eligibility(KTP, p, run_verify=False)
    assert {r["id"]: r["status"] for r in elig["rules"]}["experience_escrow"] == "unclear"


def test_verify_is_idempotent(studio_profile):
    elig = eligibility.check_eligibility(KTP, studio_profile)
    run_id = elig["run_id"]
    before = len(R.list_receipts(run_id))
    again = verifier.verify(run_id)
    assert len(R.list_receipts(run_id)) == before
    assert {r["receipt_id"] for r in again} <= {r["receipt_id"] for r in elig["receipts"]}


def test_pack_refused_before_verify():
    res = pack.build_pack("run_nothing_here", KTP)
    assert res["built"] is False and res["ready"] is False
