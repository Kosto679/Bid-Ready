"""CPV (Common Procurement Vocabulary) codes: a curated subset, labels, and keyword guessing.

CODES is a curated subset of CPV 2008, written by hand for this project: all of division 72 (IT services)
down to the 5-digit groups, the main division 48 (software packages) codes, closely related business /
design / training codes, and the top-level code of every CPV division so non-IT companies still get a
division. It is NOT the full official list (~9,500 codes). Any code a model suggests must be in CODES.
Codes are stored without the check digit (72000000, not 72000000-5); TED notices use the same form.
"""
from __future__ import annotations

import re

CODES: dict[str, str] = {
    # --- division 72: IT services -------------------------------------------------------------
    "72000000": "IT services: consulting, software development, Internet and support",
    "72100000": "Hardware consultancy services",
    "72200000": "Software programming and consultancy services",
    "72210000": "Programming services of packaged software products",
    "72212000": "Programming services of application software",
    "72212730": "Security software development services",
    "72220000": "Systems and technical consultancy services",
    "72221000": "Business analysis consultancy services",
    "72222000": "Information systems or technology strategic review and planning services",
    "72224000": "Project management consultancy services",
    "72230000": "Custom software development services",
    "72240000": "Systems analysis and programming services",
    "72250000": "System and support services",
    "72260000": "Software-related services",
    "72261000": "Software support services",
    "72262000": "Software development services",
    "72263000": "Software implementation services",
    "72265000": "Software configuration services",
    "72266000": "Software consultancy services",
    "72267000": "Software maintenance and repair services",
    "72268000": "Software supply services",
    "72300000": "Data services",
    "72310000": "Data-processing services",
    "72312000": "Data entry services",
    "72314000": "Data collection and collation services",
    "72316000": "Data analysis services",
    "72317000": "Data storage services",
    "72320000": "Database services",
    "72400000": "Internet services",
    "72410000": "Provider services",
    "72413000": "World wide web (www) site design services",
    "72415000": "World wide web (www) site operation host services",
    "72420000": "Internet development services",
    "72421000": "Internet or intranet client application development services",
    "72500000": "Computer-related services",
    "72510000": "Computer-related management services",
    "72590000": "Computer-related professional services",
    "72600000": "Computer support and consultancy services",
    "72610000": "Computer support services",
    "72700000": "Computer network services",
    "72800000": "Computer audit and testing services",
    "72810000": "Computer audit services",
    "72820000": "Computer testing services",
    "72900000": "Computer back-up and catalogue conversion services",
    # --- division 48: software packages and information systems ---------------------------------
    "48000000": "Software package and information systems",
    "48100000": "Industry specific software package",
    "48200000": "Networking, Internet and intranet software package",
    "48300000": "Document creation, drawing, imaging, scheduling and productivity software package",
    "48400000": "Business transaction and personal business software package",
    "48600000": "Database and operating software package",
    "48700000": "Software package utilities",
    "48800000": "Information systems and servers",
    "48900000": "Miscellaneous software package and computer systems",
    # --- related services ---------------------------------------------------------------------
    "30200000": "Computer equipment and supplies",
    "64200000": "Telecommunications services",
    "71300000": "Engineering services",
    "79340000": "Advertising and marketing services",
    "79400000": "Business and management consultancy and related services",
    "79410000": "Business and management consultancy services",
    "79822500": "Graphic design services",
    "80500000": "Training services",
    "80533100": "Computer training services",
    # --- one top-level code per CPV division --------------------------------------------------
    "03000000": "Agricultural, farming, fishing, forestry and related products",
    "09000000": "Petroleum products, fuel, electricity and other sources of energy",
    "14000000": "Mining, basic metals and related products",
    "15000000": "Food, beverages, tobacco and related products",
    "16000000": "Agricultural machinery",
    "18000000": "Clothing, footwear, luggage articles and accessories",
    "19000000": "Leather and textile fabrics, plastic and rubber materials",
    "22000000": "Printed matter and related products",
    "24000000": "Chemical products",
    "30000000": "Office and computing machinery, equipment and supplies except furniture and software packages",
    "31000000": "Electrical machinery, apparatus, equipment and consumables; lighting",
    "32000000": "Radio, television, communication, telecommunication and related equipment",
    "33000000": "Medical equipments, pharmaceuticals and personal care products",
    "34000000": "Transport equipment and auxiliary products to transportation",
    "35000000": "Security, fire-fighting, police and defence equipment",
    "37000000": "Musical instruments, sport goods, games, toys, handicraft, art materials and accessories",
    "38000000": "Laboratory, optical and precision equipments (excl. glasses)",
    "39000000": "Furniture (incl. office furniture), furnishings, domestic appliances (excl. lighting) and cleaning products",
    "41000000": "Collected and purified water",
    "42000000": "Industrial machinery",
    "43000000": "Machinery for mining, quarrying, construction equipment",
    "44000000": "Construction structures and materials; auxiliary products to construction (except electric apparatus)",
    "45000000": "Construction work",
    "50000000": "Repair and maintenance services",
    "51000000": "Installation services (except software)",
    "55000000": "Hotel, restaurant and retail trade services",
    "60000000": "Transport services (excl. Waste transport)",
    "63000000": "Supporting and auxiliary transport services; travel agencies services",
    "64000000": "Postal and telecommunications services",
    "65000000": "Public utilities",
    "66000000": "Financial and insurance services",
    "70000000": "Real estate services",
    "71000000": "Architectural, construction, engineering and inspection services",
    "73000000": "Research and development services and related consultancy services",
    "75000000": "Administration, defence and social security services",
    "76000000": "Services related to the oil and gas industry",
    "77000000": "Agricultural, forestry, horticultural, aquacultural and apicultural services",
    "79000000": "Business services: law, marketing, consulting, recruitment, printing and security",
    "80000000": "Education and training services",
    "85000000": "Health and social work services",
    "90000000": "Sewage, refuse, cleaning and environmental services",
    "92000000": "Recreational, cultural and sporting services",
    "98000000": "Other community, social and personal services",
}


def digits(code: str) -> str:
    return re.sub(r"\D", "", str(code).split("-")[0])


def valid(code: str) -> bool:
    return digits(code) in CODES


def label(code: str) -> str:
    d = digits(code)
    return CODES.get(d) or f"(not in our list) {d}"


def division(code: str) -> str:
    d = digits(code)[:2]
    return CODES.get(d + "000000", "other")


# Keyword rules (offline fallback). Word-boundary patterns so "approach" doesn't count as "app".
KEYWORDS: list[tuple[str, list[str]]] = [
    (r"\bsoftware\b|\bsaas\b|λογισμικ", ["72000000", "72262000"]),
    (r"\bweb\b|\bwebsites?\b|\bweb ?apps?\b|ιστοσελ|ιστότοπ", ["72413000", "72420000"]),
    (r"\bapps?\b|\bapplications?\b|\bmobile\b|εφαρμογ", ["72212000"]),
    (r"\bplatforms?\b|\bportals?\b|πλατφόρμ", ["72230000"]),
    (r"\bcustom\b|\bbespoke\b|\bdevelop(s|ment|ers?)?\b|ανάπτυξ", ["72230000"]),
    (r"\bconsult(ing|ancy|ants?)?\b|σύμβουλ", ["72220000"]),
    (r"\bdata\b|\banalytics\b|\bdashboards?\b|\bbi\b|δεδομέν", ["72316000"]),
    (r"\bdatabases?\b|βάσεις δεδομένων", ["72320000"]),
    (r"\bai\b|\bmachine learning\b|\bml\b|τεχνητή νοημοσύνη", ["72316000", "73000000"]),
    (r"\bcloud\b|\bhosting\b|\bdevops\b|φιλοξεν", ["72415000"]),
    (r"\bsupport\b|\bhelp ?desk\b|υποστήριξ", ["72261000"]),
    (r"\bmaintenance\b|συντήρησ", ["72267000"]),
    (r"\bsecurity\b|\bcyber", ["72212730"]),
    (r"\btesting\b|\bqa\b|\baudit\b", ["72800000"]),
    (r"\bnetworks?\b|\binfrastructure\b|δίκτυ", ["72700000"]),
    (r"\b(ux|ui)\b|\bgraphic design\b|\bbranding\b", ["79822500"]),
    (r"\bmarketing\b|\badvertising\b", ["79340000"]),
    (r"\btraining\b|\be-?learning\b|εκπαίδευσ", ["80500000"]),
    (r"\bconstruction\b|\bbuilding works?\b|κατασκευ", ["45000000"]),
    (r"\bcatering\b|\brestaurants?\b|\bhotels?\b", ["55000000"]),
    (r"\bcleaning\b|\bwaste\b", ["90000000"]),
    (r"\bmedical\b|\bhealth ?care\b|υγεί", ["85000000"]),
]


def keyword_guess(text: str, limit: int = 8) -> list[dict]:
    """Return [{code, label, reason, source}] from keyword rules, in rule order, deduplicated."""
    low = (text or "").lower()
    out: list[dict] = []
    for pat, codes in KEYWORDS:
        m = re.search(pat, low)
        if not m:
            continue
        for c in codes:
            if c not in {o["code"] for o in out}:
                out.append({"code": c, "label": CODES[c], "reason": f'you wrote "{m.group(0).strip()}"', "source": "keywords"})
    return out[:limit]


def guess(text: str, model_fn=None) -> dict:
    """Pick CPV codes for a company description.

    Uses Gemini (choosing only from CODES) when configured, else keyword rules. Returns
    {"codes": [...], "detail": [{code, label, reason, source}], "source": "gemini"|"keywords", "rejected": [...], "note": str}.
    `model_fn(text) -> [{"code","reason"}]` can be injected (tests).
    """
    rejected: list[str] = []
    note = ""
    if model_fn is None:
        from . import gemini

        ok, why = gemini.configured()
        model_fn = gemini.suggest_cpv if ok else None
        note = "" if ok else f"Gemini not used: {why}"
    if model_fn is not None and (text or "").strip():
        try:
            raw = model_fn(text) or []
            detail = []
            for item in raw:
                c = digits(item.get("code", ""))
                if c in CODES and c not in {d["code"] for d in detail}:
                    detail.append({"code": c, "label": CODES[c], "reason": (item.get("reason") or "").strip(), "source": "gemini"})
                elif c not in CODES:
                    rejected.append(item.get("code", ""))
            if detail:
                return {"codes": [d["code"] for d in detail[:6]], "detail": detail[:6], "source": "gemini", "rejected": rejected,
                        "note": f"Rejected codes not in our list: {', '.join(rejected)}" if rejected else ""}
            note = "Gemini returned no usable codes; used keyword rules."
        except Exception as e:  # network, auth, quota
            note = f"Gemini failed ({type(e).__name__}); used keyword rules."
    detail = keyword_guess(text)
    return {"codes": [d["code"] for d in detail], "detail": detail, "source": "keywords", "rejected": rejected, "note": note}


def prompt_list(prefixes: tuple[str, ...] | None = None) -> str:
    return "\n".join(f"{c} {l}" for c, l in CODES.items() if not prefixes or c.startswith(prefixes))
