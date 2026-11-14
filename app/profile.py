"""Onboarding: two typed lines (or JSON) -> CompanyProfile. Ask only for what we could not work out.

The three questions we always need answered by a human: 3-year turnover total, certificates,
public-sector projects in the last 5 years. A skipped projects question stays null so
eligibility marks experience UNCLEAR (not missing).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .receipts import new_run_id, write_receipt

CITY_NUTS = {
    "athens": "EL30", "αθήνα": "EL30", "attica": "EL30", "αττική": "EL30",
    "thessaloniki": "EL52", "θεσσαλονίκη": "EL52",
    "patras": "EL63", "πάτρα": "EL63",
    "heraklion": "EL43", "ηράκλειο": "EL43",
    "ioannina": "EL54", "larissa": "EL61", "volos": "EL61",
}

CPV_HINTS = [
    (r"software|app|web|platform|saas|develop|λογισμικ|εφαρμογ", ["72000000", "72200000", "72260000"]),
    (r"consult|σύμβουλ", ["72220000"]),
    (r"data|analytics|ai\b|machine learning|δεδομέν", ["72300000", "72316000"]),
    (r"cloud|hosting|devops|φιλοξεν", ["72400000", "72415000"]),
    (r"support|maintenance|υποστήριξ|συντήρησ", ["72250000", "72267000"]),
    (r"security|cyber|ασφάλει", ["72212730"]),
]

QUESTIONS = {
    "turnover_2023_2025_total_eur": "What was your total turnover for 2023 + 2024 + 2025 combined (EUR)?",
    "certificates": "Which certificates do you hold (e.g. ISO 9001, ISO 27001)? Say 'none' if none.",
    "public_sector_projects_last_5y": "Which public-sector projects have you delivered in the last 5 years? Say 'none' if none.",
}


def _parse_lines(text: str) -> dict[str, Any]:
    t = text.strip()
    low = t.lower()
    name = None
    m = re.match(r"\s*([^\n,.]{2,60}?)\s+(?:is|are|—|-|:)\s", t)
    if m:
        name = m.group(1).strip()
    size = None
    m = re.search(r"(\d{1,5})\s*[- ]?\s*(?:person|people|employees|staff|άτομα|εργαζόμεν)", low)
    if m:
        size = int(m.group(1))
    location, nuts = None, None
    for city, code in CITY_NUTS.items():
        if city in low:
            location, nuts = city.title() + ", Greece", code
            break
    if not location and ("greece" in low or "ελλάδα" in low):
        location, nuts = "Greece", "GRC"
    cpvs: list[str] = []
    for pat, codes in CPV_HINTS:
        if re.search(pat, low):
            cpvs += [c for c in codes if c not in cpvs]
    return {
        "name": name or "Your company",
        "summary": t.replace("\n", " "),
        "size": size,
        "location": location,
        "nuts_or_country": nuts,
        "cpv_codes": cpvs,
    }


def _parse_eur(v: Any) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).lower().replace("€", "").replace("eur", "").strip()
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    s = s.replace(",", "").replace(" ", "")
    if s.count(".") > 1 or re.fullmatch(r"\d{1,3}\.\d{3}", s):  # Greek thousands separator
        s = s.replace(".", "")
    try:
        return int(float(s) * mult)
    except ValueError:
        return None


def _parse_certs(v: Any) -> list[str]:
    if v is None:
        return []
    items = v if isinstance(v, list) else re.split(r"[,;\n]| and ", str(v))
    out = []
    for i in items:
        i = str(i).strip()
        if i and i.lower() not in ("none", "no", "κανένα", "-"):
            out.append(i)
    return out


def apply_answers(profile: dict, answers: dict | None) -> dict:
    answers = answers or {}
    p = dict(profile)
    if "turnover_2023_2025_total_eur" in answers:
        p["turnover_2023_2025_total_eur"] = _parse_eur(answers["turnover_2023_2025_total_eur"])
    if "certificates" in answers:
        p["certificates"] = _parse_certs(answers["certificates"])
        p["_certificates_answered"] = True
    if "public_sector_projects_last_5y" in answers:
        v = answers["public_sector_projects_last_5y"]
        # Skipped (null / empty / "skip") stays null -> experience UNCLEAR later.
        p["public_sector_projects_last_5y"] = None if v in (None, "", "skip") else v
    if "profitable_last_3y" in answers:
        p["profitable_last_3y"] = answers["profitable_last_3y"]
    return p


def missing_questions(profile: dict) -> list[dict]:
    qs = []
    if profile.get("turnover_2023_2025_total_eur") is None:
        qs.append({"field": "turnover_2023_2025_total_eur", "question": QUESTIONS["turnover_2023_2025_total_eur"]})
    if not profile.get("certificates") and not profile.get("_certificates_answered"):
        qs.append({"field": "certificates", "question": QUESTIONS["certificates"]})
    if profile.get("public_sector_projects_last_5y") is None:
        qs.append({"field": "public_sector_projects_last_5y", "question": QUESTIONS["public_sector_projects_last_5y"]})
    return qs


def onboard(lines: str = "", answers: dict | None = None, profile_json: dict | None = None, run_id: str | None = None) -> dict:
    run_id = run_id or new_run_id()
    base: dict[str, Any] = {
        "name": None, "summary": "", "size": None, "location": None, "nuts_or_country": None,
        "cpv_codes": [], "turnover_2023_2025_total_eur": None, "certificates": [],
        "public_sector_projects_last_5y": None, "profitable_last_3y": None,
    }
    source = "json"
    if profile_json:
        base.update(profile_json)
    else:
        parsed = None
        try:
            from . import llm

            parsed = llm.extract_profile(lines)
            source = "llm" if parsed else "rules"
        except Exception:
            parsed = None
        base.update(parsed or _parse_lines(lines))
        if not parsed:
            source = "rules"
    profile = apply_answers(base, answers)
    questions = missing_questions(profile)
    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"onboard:{run_id}:{hashlib.sha1(repr((lines, answers, profile_json)).encode()).hexdigest()[:12]}",
        "action": "onboard",
        "intent": {"input": lines[:500] if lines else "profile_json"},
        "tool_call": {"name": "onboard", "arguments": {"source": source}},
        "tool_response": {"profile": {k: v for k, v in profile.items() if not k.startswith('_')}, "open_questions": [q["field"] for q in questions]},
        "status": "RECORDED",
    })
    return {"run_id": run_id, "profile": profile, "questions": questions, "source": source, "receipt": receipt}


DEMO_LINES = (
    "Pixelridge is an 8-person software studio in Athens.\n"
    "We build web apps, booking platforms and data dashboards for tourism and retail clients."
)

DEMO_ANSWERS = {
    "turnover_2023_2025_total_eur": 350000,
    "certificates": "ISO 9001",
    "public_sector_projects_last_5y": "Two small municipal websites (2023, 2025); no escrow-payment systems.",
    "profitable_last_3y": True,
}
