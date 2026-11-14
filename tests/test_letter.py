"""The consortium letter: Greek only, tender-specific facts that match the RFP pages, and the rewrite fact check."""
import re

from app import eligibility, letter
from app import tender_source as T

KTP = "769674-2026"


def test_tender_facts_match_rfp_pages():
    p17 = T.norm(T.page_text(KTP, 17))
    assert "(200.000,00 €) πλέον ΦΠΑ" in p17
    assert "125.000,00 € αφορά τις υπηρεσίες υποστήριξης και συντήρησης" in p17
    assert "75.000,00 € αφορά υπηρεσίες παραμετροποίησης" in p17
    assert "δώδεκα (12) μήνες" in p17
    p11 = T.norm(T.page_text(KTP, 11))
    assert "07-12-2026 ημέρα Δευτέρα και ώρα 14:00" in p11
    assert "11-12-2026 ημέρα Παρασκευή" in p11


def test_letter_is_greek_and_tender_specific(studio_profile):
    elig = eligibility.check_eligibility(KTP, studio_profile)
    res = letter.draft_cover_letter(KTP, studio_profile, elig)
    md = res["markdown"]
    assert res["source"] == "template"  # offline: no Gemini
    allowed = {"escrow", "accounts", "iso", "sla", "mis", "web", "dashboards", "bid-ready", "proc", "pixelridge"}
    latin = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]+", md)} - allowed
    assert not latin, f"English words in letter: {latin}"
    for fact in ("125.000 €", "75.000 €", "12 μήνες", "4.000 €", "§2.2.9.2 Β.10", "MIS"):
        assert fact in md
    assert "6.000" not in md


def test_fact_check_rejects_new_numbers_and_english(studio_profile):
    draft = "Ο προϋπολογισμός είναι 200.000 € και υποβάλλεται στο ΕΣΗΔΗΣ."
    ok, _ = letter.fact_check("Ο προϋπολογισμός ανέρχεται σε 200.000 € και υποβάλλεται στο ΕΣΗΔΗΣ.", draft, studio_profile)
    assert ok
    bad, info = letter.fact_check("Ο προϋπολογισμός είναι 300.000 € στο ΕΣΗΔΗΣ.", draft, studio_profile)
    assert not bad and "300000" in info["new_numbers"]
    bad2, info2 = letter.fact_check("We would love to partner with you on this tender. ΕΣΗΔΗΣ 200.000 €", draft, studio_profile)
    assert not bad2 and info2["unexpected_latin_words"]
