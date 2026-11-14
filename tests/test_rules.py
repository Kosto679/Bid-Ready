"""Generic rule reader: any source, verified quotes and arithmetic, profile comparison, agreement score."""
from app import eligibility, rules as RL, verifier
from app import tender_source as T

KTP = "769674-2026"


def _q(pg, anchor, after=120):
    t = T.norm(T.page_text(KTP, pg))
    i = t.find(anchor)
    assert i >= 0, anchor
    return t[i:i + len(anchor) + after]


def ktp_reader(ctx):
    """A correct reader for ΚτΠ: real quotes from real pages."""
    return {
        "budget": {"amount_eur": 200000, "quote": _q(17, "ανέρχεται σε διακόσιες χιλιάδες ευρώ (200.000,00 €)", 10), "ref": "p17"},
        "turnover": {"min_eur": 400000, "basis": "total", "years": "2023-2025", "percent_of_budget": 200,
                     "quote": _q(33, "διακόσια τοις εκατό (200%)", 60), "ref": "p33"},
        "experience": {"summary": "Five public escrow-payment projects.", "min_projects": 5, "quote": _q(33, "I. Πέντε (5) τουλάχ", 40), "ref": "p33"},
        "iso": {"standards": ["9001"], "quote": _q(36, "ISO 9001:2015", 20), "ref": "p36"},
        "team": {"roles": [], "quote": None, "ref": None},
        "guarantee": {"amount_eur": 4000, "percent": 2, "quote": _q(27, "ποσοστό 2% του προϋπολογισμού", 120), "ref": "p27"},
    }


def test_ted_blocks_from_cached_ktp_notice():
    b = T.ted_blocks(KTP)
    assert any(k.startswith("C") for k in b) and "G1" in b
    assert "300000" in b["V1"]["text"] and "200000" in b["V1"]["text"]


def test_read_and_verify_ktp_with_correct_reader():
    r = RL.read(KTP, reader=ktp_reader)
    assert r["source"]["kind"] == "pack"
    rec = {x["intent"]["claim_id"]: x["status"] for x in verifier.verify("rules_t1", r["claims"])}
    assert rec["rule:budget"] == rec["rule:turnover"] == rec["rule:guarantee"] == "VERIFIED"
    assert rec["rule:guarantee:arith"] == rec["rule:turnover:arith"] == "VERIFIED"
    a = RL.agreement_with_index(r["rules"])
    assert a["total"] == 6 and a["agree"] == 5  # the stand-in reader only lists one ISO


def test_wrong_amount_fails_quote_and_arithmetic():
    def wrong(ctx):
        d = ktp_reader(ctx)
        d["guarantee"] = {**d["guarantee"], "amount_eur": 6000}
        return d
    r = RL.read(KTP, reader=wrong)
    rec = {x["intent"]["claim_id"]: x["status"] for x in verifier.verify("rules_t2", r["claims"])}
    assert rec["rule:guarantee"] == "FAILED" and rec["rule:guarantee:arith"] == "FAILED"


def test_compare_with_profile(studio_profile):
    rows = {r["id"]: r for r in RL.compare(ktp_reader(""), studio_profile)}
    assert rows["turnover"]["status"] == "missing"          # 350k < 400k total
    assert rows["iso"]["status"] == "meets"                  # stand-in rule only asks 9001
    avg = RL.compare({"turnover": {"min_eur": 100000, "basis": "average", "quote": "x"}}, studio_profile)[0]
    assert avg["status"] == "meets"                          # 350k / 3 = 116k per year >= 100k


def test_notice_without_published_criteria_says_so(studio_profile, monkeypatch):
    from app import ted
    xml = ('<n xmlns:cac="c" xmlns:cbc="b"><cac:ProcurementProject><cac:RequestedTenderTotal>'
           '<cbc:EstimatedOverallContractAmount>50000</cbc:EstimatedOverallContractAmount></cac:RequestedTenderTotal></cac:ProcurementProject></n>')
    monkeypatch.setattr(ted, "notice_xml", lambda pub: (xml, "ted_live"))
    out = eligibility.check_eligibility("999999-2026", studio_profile)
    assert out["verdict"] == "unclear" and out["rules"] == [] and "only in the tender documents" in out["source"]["note"]
