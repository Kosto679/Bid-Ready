"""Live extraction on the unannotated ΟΛΠΑ tender, with stand-in readers (no network)."""
from app import live_extract as LX
from app import tender_source as T

PACK = "backup-OLPA-26PROC020181047"


def honest(question, context):
    """Answers like a correct model would: real quotes from the real pages."""
    if "estimated value" in question:
        anchor = "Ο συνολικός προϋπολογισμός για τις ζητούμενες υπηρεσίες ανέρχεται"
        return {"value": "280000", "quote": _span(7, anchor, 90), "pdf_page": 7}
    if "participation guarantee" in question:
        return {"value": "5600", "quote": "ποσού πέντε χιλιάδων εξακοσίων ευρώ (5.600€)", "pdf_page": 17}
    if "deadline" in question:
        return {"value": "2026-12-01T11:00", "quote": _span(10, "Η καταληκτική ημερομηνία παραλαβής των προσφορών", 60), "pdf_page": 10}
    return {"value": None, "quote": None, "pdf_page": None}


def _span(pg, anchor, after):
    t = T.norm(T.pack_page(PACK, pg))
    i = t.find(anchor)
    assert i >= 0, (pg, anchor)
    return t[i:i + len(anchor) + after]


def test_pages_come_from_the_pdf_text():
    pages = T.pack_pages(PACK)
    assert len([p for p in pages if p.strip()]) == 98
    assert "5.600" in T.norm(T.pack_page(PACK, 17))


def test_correct_reader_is_verified_and_arithmetic_holds():
    r = LX.run(reader=honest)
    f = r["fields"]
    assert f["participation_guarantee_eur"]["status"] == "VERIFIED"
    assert f["initial_value_ex_vat_eur"]["status"] == "VERIFIED"
    assert f["submission_deadline"]["status"] == "VERIFIED"
    assert f["iso_standards"]["status"] == "UNVERIFIED"          # reader abstained: nothing to verify
    assert r["arithmetic"]["status"] == "VERIFIED" and r["arithmetic"]["observed"]["expected"] == 5600


def test_wrong_value_with_real_quote_fails():
    def wrong(q, c):
        a = honest(q, c)
        if "participation guarantee" in q:
            a = {**a, "value": "6000"}       # right page, right quote, wrong number
        return a
    r = LX.run(reader=wrong)
    assert r["fields"]["participation_guarantee_eur"]["status"] == "FAILED"
    assert r["arithmetic"]["status"] == "FAILED"   # 2% x 280,000 = 5,600, not 6,000


def test_invented_quote_fails():
    def invent(q, c):
        a = honest(q, c)
        if "participation guarantee" in q:
            a = {"value": "5600", "quote": "εγγύηση συμμετοχής 5.600€ για όλους", "pdf_page": 17}
        return a
    r = LX.run(reader=invent)
    g = r["fields"]["participation_guarantee_eur"]
    assert g["status"] == "FAILED"
    rec = next(x for x in r["receipts"] if x["intent"]["claim_id"] == "live:participation_guarantee_eur")
    assert rec["independent_check"]["observed"]["quote_on_page"] is False
