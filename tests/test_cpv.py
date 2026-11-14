"""CPV guessing: curated list, keyword fallback, and validation of model suggestions."""
from app import cpv, profile


def test_codes_are_well_formed():
    assert all(len(c) == 8 and c.isdigit() for c in cpv.CODES)
    assert all(c in cpv.CODES for _, codes in cpv.KEYWORDS for c in codes)


def test_keywords_demo_studio_with_reasons():
    got = cpv.keyword_guess(profile.DEMO_LINES)
    codes = [g["code"] for g in got]
    assert "72000000" in codes and "72316000" in codes  # software + data dashboards
    assert all(g["reason"].startswith("you wrote") for g in got)


def test_keywords_word_boundaries():
    assert cpv.keyword_guess("Our approach is careful") == []          # "approach" is not "app"
    assert [g["code"] for g in cpv.keyword_guess("We run a catering company")] == ["55000000"]


def test_model_codes_are_validated_and_invalid_ones_rejected():
    fake = lambda text: [{"code": "72230000-6", "reason": "custom software"}, {"code": "99999999", "reason": "made up"},
                         {"code": "72230000", "reason": "duplicate"}]
    g = cpv.guess("custom software", model_fn=fake)
    assert g["source"] == "gemini" and g["codes"] == ["72230000"]
    assert g["rejected"] == ["99999999"] and "99999999" in g["note"]


def test_model_failure_falls_back_to_keywords():
    def boom(text):
        raise TimeoutError("vertex")
    g = cpv.guess("we build web apps", model_fn=boom)
    assert g["source"] == "keywords" and g["codes"] and "Gemini failed" in g["note"]


def test_onboarding_offline_uses_keywords_and_respects_removed_codes():
    r = profile.onboard(profile.DEMO_LINES)
    p = r["profile"]
    assert p["cpv_source"] == "keywords" and p["cpv_detail"]
    keep = p["cpv_codes"][:2]
    r2 = profile.onboard(profile.DEMO_LINES, answers={"cpv_codes": keep + ["12345678"]})
    assert r2["profile"]["cpv_codes"] == keep
    assert [d["code"] for d in r2["profile"]["cpv_detail"]] == keep
