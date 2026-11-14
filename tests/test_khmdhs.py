"""ΚΗΜΔΗΣ client and TED -> ΚΗΜΔΗΣ matching, with the network stubbed."""
import json

import pytest

from app import config, khmdhs as K


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)


def rec(adam, title, cost, esidis=(), notice_type="Διακήρυξη", deadline="2026-12-07T14:00:00"):
    return {"referenceNumber": adam, "title": title, "totalCostWithoutVAT": cost, "finalSubmissionDate": deadline,
            "systemicNumbers": [{"systemicNumber": e} for e in esidis], "noticeType": {"value": notice_type},
            "organization": {"value": "ΔΗΜΟΣ"}, "cancelled": False}


def stub(monkeypatch, records, ted_xml, ted_title="Escrow platform support"):
    seen = []

    def fake_search(criteria, page=0, timeout=30):
        seen.append(criteria)
        lo, hi = criteria.get("totalCostFrom", 0), criteria.get("totalCostTo", 1e12)
        hits = [r for r in records if lo <= r["totalCostWithoutVAT"] <= hi]
        return {"content": hits, "totalElements": len(hits), "totalPages": 1}

    from app import ted
    monkeypatch.setattr(K, "search", fake_search)
    monkeypatch.setattr(ted, "notice_xml", lambda pub: (ted_xml, "ted_live"))
    monkeypatch.setattr(ted, "get_notice", lambda pub, run_id=None: {"notice": {"title": ted_title, "buyer_name": "ΚτΠ"}})
    return seen


XML = ("<n><cac:TenderSubmissionDeadlinePeriod><cbc:EndDate>2026-12-07+02:00</cbc:EndDate></cac:TenderSubmissionDeadlinePeriod>"
       "<cbc:EstimatedOverallContractAmount currencyID='EUR'>300000</cbc:EstimatedOverallContractAmount>"
       "<cbc:EstimatedOverallContractAmount currencyID='EUR'>200000</cbc:EstimatedOverallContractAmount>{uri}</n>")


def test_is_adam_and_normalize():
    assert K.is_adam("26PROC020137847") and not K.is_adam("769674-2026")
    n = K.normalize(rec("26PROC020137847", "x", 200000, ["589064"]))
    assert n["adam"] == "26PROC020137847" and n["esidis"] == ["589064"] and n["cost_ex_vat"] == 200000


def test_match_by_esidis_number_and_value(monkeypatch):
    records = [rec("26PROC000000001", "Other tender", 200000, ["111111"]),
               rec("26PROC020137847", "Escrow accounts support", 200000, ["589064"])]
    seen = stub(monkeypatch, records, XML.format(uri="<cbc:URI>https://x/actSearch/resources/search/589064</cbc:URI>"))
    m = K.match_ted("769674-2026")
    assert m["adam"] == "26PROC020137847" and m["how"].startswith("ΕΣΗΔΗΣ number 589064")
    assert any("totalCostFrom" in c and c["finalDateFrom"] == "2026-12-07 00:00" for c in seen)   # narrowed by value + day


def test_match_by_title_without_esidis(monkeypatch):
    records = [rec("26PROC000000001", "Cleaning services", 200000),
               rec("26PROC020137847", "Escrow platform support services", 200000)]
    stub(monkeypatch, records, XML.format(uri=""), ted_title="Ελλάδα – IT – Escrow platform support services")
    m = K.match_ted("769674-2026", use_gemini=False)
    assert m["adam"] == "26PROC020137847" and "title" in m["how"]


def test_prefers_full_notice_over_summary(monkeypatch):
    records = [rec("26PROC020137800", "Escrow support", 200000, ["589064"], notice_type="Περίληψη"),
               rec("26PROC020137847", "Escrow support", 200000, ["589064"], notice_type="Διακήρυξη")]
    stub(monkeypatch, records, XML.format(uri="<cbc:URI>search/589064</cbc:URI>"))
    assert K.match_ted("769674-2026")["adam"] == "26PROC020137847"


def test_no_candidate_no_match_and_cached(monkeypatch):
    stub(monkeypatch, [rec("26PROC000000001", "Other", 999999)], XML.format(uri=""))
    assert K.match_ted("769674-2026", use_gemini=False) is None
    cache = json.loads((config.DATA_DIR / K.CACHE / "ted-matches.json").read_text(encoding="utf-8"))
    assert cache["769674-2026"] is None


def test_404_means_no_results(monkeypatch):
    class R:
        status_code = 404
    class C:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k): return R()
    monkeypatch.setattr(K.httpx, "Client", C)
    assert K.search({"title": "nothing"}) == {"content": [], "totalElements": 0, "totalPages": 0}
