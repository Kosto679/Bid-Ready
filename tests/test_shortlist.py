"""Shortlist: search by the profile's CPV divisions and score everything before cutting to the top N."""
from app import agent, ted


def test_cpv_clause():
    assert ted.cpv_clause("72*") == "classification-cpv = 72*"
    assert ted.cpv_clause(["72", "48"]) == "(classification-cpv = 72* OR classification-cpv = 48*)"


def test_query_uses_profile_divisions(monkeypatch):
    seen = {}

    def fake_search(q, limit, cache_name):
        seen.update(q=q, limit=limit, cache=cache_name)
        return [], "ted_live", None, 0

    monkeypatch.setattr(ted, "_search", fake_search)
    monkeypatch.setattr(ted, "get_notice", lambda pub, run_id=None: {"notice": None})
    r = agent.shortlist({"cpv_codes": ["55300000", "15000000"]})
    assert "(classification-cpv = 15* OR classification-cpv = 55*)" in seen["q"]
    assert seen["limit"] >= 100 and seen["cache"] == "search_el_15_55.json"
    assert [d["code"] for d in r["searched"]["divisions"]] == ["15", "55"]


def test_scores_all_results_before_cutting(monkeypatch):
    # 20 notices in TED order; the best fit is the LAST one. The old code kept TED's first 8.
    def n(i, cpv, days):
        return {"publication-number": f"{i}-2026", "classification-cpv": [cpv], "place-of-performance": ["EL30"],
                "deadline-receipt-tender-date-lot": [f"2026-12-{days:02d}+02:00"], "estimated-value-proc": "100000"}
    raw = [n(i, "45000000", 1) for i in range(19)] + [n(99, "72000000", 30)]
    monkeypatch.setattr(ted, "_search", lambda q, limit, cache: (raw, "ted_live", None, 20))
    monkeypatch.setattr(ted, "get_notice", lambda pub, run_id=None: {"notice": None})
    r = agent.shortlist({"cpv_codes": ["72000000"], "turnover_2023_2025_total_eur": 500000, "location": "Athens, Greece"}, limit=8)
    assert r["matches"][0]["publication_number"] == "99-2026"
    assert r["searched"]["scored"] == 20 and len(r["matches"]) == 8


def test_offline_demo_still_finds_ktp(studio_profile):
    r = agent.shortlist(studio_profile)
    assert r["source"] == "local_cache"
    assert any(m["publication_number"] == "769674-2026" for m in r["matches"])
