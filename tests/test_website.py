"""Website onboarding: facts must be quoted from the page they name; turnover is always asked."""
import re

import pytest

from app import config, profile, website

URL = "https://pixelridge.example/"


def _site_markdown() -> str:
    html = (config.ROOT / "demo-site" / "index.html").read_text(encoding="utf-8")
    body = re.sub(r"(?s)<style.*?</style>|<head.*?</head>", "", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


@pytest.fixture
def site(monkeypatch):
    s = {"url": URL, "pages": [{"url": URL, "title": "Pixelridge", "markdown": _site_markdown()}]}
    monkeypatch.setattr(website, "read_site", lambda url: s)
    return s


def F(value, quote, page=1):
    return {"value": value, "quote": quote, "page": page}


GOOD = {
    "name": F("Pixelridge", "Pixelridge was founded in 2019 in Athens"),
    "team_size": F("8", "We are a team of 8 people"),
    "city": F("Athens, Greece", "A software studio in Athens, Greece"),
    "summary": "A software studio in Athens building web apps, booking platforms and data dashboards.",
    "services": [F("Web applications", "Custom web apps and portals"), F("Data dashboards", "Reporting and analytics dashboards")],
    "certificates": [F("ISO 9001:2015", "certified to ISO 9001:2015")],
    "public_sector_projects": [F("Municipality website (2023)", "the website of a municipality in Attica (2023)")],
}


def test_site_profile_keeps_quoted_facts_and_asks_turnover(site):
    r = profile.onboard_site(URL, reader=lambda ctx: GOOD)
    p = r["profile"]
    assert (p["name"], p["size"], p["location"], p["nuts_or_country"]) == ("Pixelridge", 8, "Athens, Greece", "EL30")
    assert p["certificates"] == ["ISO 9001:2015"]
    assert p["public_sector_projects_last_5y"] == ["Municipality website (2023)"]
    assert [q["field"] for q in r["questions"]] == ["turnover_2023_2025_total_eur"]
    assert p["site"]["sources"]["team_size"]["url"] == URL
    assert r["source"] == "website"


def test_invented_facts_are_dropped(site):
    bad = dict(GOOD, team_size=F("25", "We are a team of 25 people"),
               certificates=[F("ISO 27001", "certified to ISO 27001")],
               public_sector_projects=[F("Ministry portal", "a portal for the Ministry", page=2)])
    r = profile.onboard_site(URL, reader=lambda ctx: bad)
    p = r["profile"]
    assert p["size"] is None and p["certificates"] == [] and p["public_sector_projects_last_5y"] is None
    assert p["site"]["dropped"] == 3
    assert {q["field"] for q in r["questions"]} == {"turnover_2023_2025_total_eur", "certificates", "public_sector_projects_last_5y"}


def test_answers_fill_the_rest(site):
    r = profile.onboard_site(URL, {"turnover_2023_2025_total_eur": "400k"}, reader=lambda ctx: GOOD)
    assert r["profile"]["turnover_2023_2025_total_eur"] == 400_000 and r["questions"] == []


def test_not_configured_offline():
    with pytest.raises(website.NotConfigured):
        website.read_site(URL)
