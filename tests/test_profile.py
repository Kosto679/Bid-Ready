"""Onboarding with Gemini profile reading: validated, with rule-based fallback."""
from app import gemini, profile


def _fake(monkeypatch, answer):
    monkeypatch.setattr(gemini, "configured", lambda: (True, ""))
    monkeypatch.setattr(gemini, "extract_profile", lambda text: answer)
    monkeypatch.setattr(gemini, "suggest_cpv", lambda text: [{"code": "72316000", "reason": "analytics"}])


def test_gemini_fills_profile_and_keeps_summary(monkeypatch):
    _fake(monkeypatch, {"name": "Ergon Data", "size": 8, "city": "Thessaloniki", "nuts_or_country": "EL52"})
    text = "Ergon Data is an eight-person analytics consultancy in Thessaloniki."
    r = profile.onboard(text)
    p = r["profile"]
    assert r["source"] == "gemini"
    assert (p["name"], p["size"], p["location"], p["nuts_or_country"]) == ("Ergon Data", 8, "Thessaloniki, Greece", "EL52")
    assert p["summary"] == text  # your own words, not the model's
    assert p["cpv_codes"] == ["72316000"]


def test_invented_name_and_bad_codes_are_dropped(monkeypatch):
    _fake(monkeypatch, {"name": "Acme Global Ltd", "size": -3, "city": None, "nuts_or_country": "Attica!"})
    p = profile.onboard("We are a software studio in Athens.")["profile"]
    assert p["name"] == "Your company"          # name not in the text -> rejected
    assert p["size"] is None                    # nonsense size -> rejected
    assert p["nuts_or_country"] == "EL30"       # bad code -> rules' value kept


def test_gemini_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(gemini, "configured", lambda: (True, ""))

    def boom(text):
        raise TimeoutError("vertex")

    monkeypatch.setattr(gemini, "extract_profile", boom)
    monkeypatch.setattr(gemini, "suggest_cpv", boom)
    r = profile.onboard(profile.DEMO_LINES)
    assert r["source"] == "rules" and r["profile"]["size"] == 8 and r["profile"]["cpv_source"] == "keywords"
