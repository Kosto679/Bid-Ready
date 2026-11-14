"""Estimated-value filter on the shortlist."""
from app import agent, ted


def _notices(monkeypatch, values):
    def n(i, v):
        return {"publication-number": f"{i}-2026", "classification-cpv": ["72000000"], "place-of-performance": ["EL30"],
                "deadline-receipt-tender-date-lot": ["2026-12-20+02:00"], **({"estimated-value-proc": str(v)} if v else {})}
    raw = [n(i, v) for i, v in enumerate(values)]
    monkeypatch.setattr(ted, "_search", lambda q, limit, cache: (raw, "ted_live", None, len(raw)))
    monkeypatch.setattr(ted, "get_notice", lambda pub, run_id=None: {"notice": None})


def test_default_max_is_half_the_turnover():
    assert agent.default_value_max({"turnover_2023_2025_total_eur": 350000}) == 175000
    assert agent.default_value_max({}) is None


def test_filter_hides_out_of_range_and_keeps_unknown(monkeypatch):
    _notices(monkeypatch, [50000, 150000, 900000, None])
    r = agent.shortlist({"cpv_codes": ["72000000"], "turnover_2023_2025_total_eur": 350000, "location": "Athens"},
                        value_min=100000, value_max=175000)
    pubs = {m["publication_number"]: m for m in r["matches"]}
    assert set(pubs) == {"1-2026", "3-2026"}                  # 150k inside, unknown kept
    assert pubs["3-2026"]["value_unknown"] is True
    f = r["searched"]["filter"]
    assert f["hidden"] == 2 and f["unknown_value"] == 1 and f["default_max"] == 175000


def test_no_filter_keeps_everything(monkeypatch):
    _notices(monkeypatch, [50000, 900000])
    r = agent.shortlist({"cpv_codes": ["72000000"], "turnover_2023_2025_total_eur": 350000})
    assert len(r["matches"]) == 2 and r["searched"]["filter"]["hidden"] == 0


def test_demo_tender_pinned_with_reason_when_filtered_out(studio_profile):
    r = agent.shortlist(studio_profile, value_max=175000)     # offline cache; ΚτΠ is €300k on TED
    ktp = next(m for m in r["matches"] if m["publication_number"] == "769674-2026")
    assert ktp["pinned"] and ktp["pinned_reason"] == "outside your value range"
