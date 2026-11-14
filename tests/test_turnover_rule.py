"""The shortlist score uses a tender's verified turnover rule when known, else the rule of thumb."""
from datetime import date

from app import eligibility, rule_cache, scoring

KTP = {"publication_number": "769674-2026", "classification_cpv": ["72000000"], "estimated_value": 300000.0,
       "place_of_performance": ["EL304"], "deadline_date": "2026-12-07"}
TODAY = date(2026, 11, 15)


def test_rule_of_thumb_without_a_known_rule(studio_profile):
    s = scoring.score_one(KTP, studio_profile, TODAY)
    assert s["factors"]["value_source"] == "rule_of_thumb"
    assert abs(s["factors"]["value_fit"] - 350000 / 600000) < 0.01


def test_total_rule_used_when_known(studio_profile):
    s = scoring.score_one(KTP, studio_profile, TODAY, {"min_eur": 400000, "basis": "total"})
    assert s["factors"]["value_source"] == "tender_rule"
    assert abs(s["factors"]["value_fit"] - 350000 / 400000) < 0.01
    assert "3-year total" in s["explain"]["value_fit"] and "€400,000" in s["reason"]


def test_average_rule_is_stricter(studio_profile):
    s = scoring.score_one(KTP, studio_profile, TODAY, {"min_eur": 400000, "basis": "average"})
    assert abs(s["factors"]["value_fit"] - (350000 / 3) / 400000) < 0.01
    assert "yearly turnover" in s["explain"]["value_fit"]


def test_ktp_check_saves_the_verified_rule_and_shortlist_uses_it(studio_profile):
    assert rule_cache.get("769674-2026") is None
    eligibility.check_eligibility("769674-2026", studio_profile)
    assert rule_cache.get("769674-2026")["min_eur"] == 400000
    s = scoring.score_tenders([KTP], studio_profile)["scored"][0]
    assert s["factors"]["value_source"] == "tender_rule"


def test_unverified_rule_is_not_saved():
    rule_cache.save_from_receipts("x-2026", [{"status": "FAILED", "intent": {"claim_id": "rule:turnover"}}],
                                  {"turnover": {"min_eur": 1, "basis": "total"}})
    assert rule_cache.get("x-2026") is None
