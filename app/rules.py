"""Generic rule reader: eligibility rules for ANY tender, read from whatever text we have.

Source, in order of preference:
  1. a local tender pack (PDF page text): ΚτΠ, ΟΛΠΑ
  2. the TED notice's own eForms text (selection criteria, guarantee, values), when the buyer filled it in
  3. nothing machine-readable -> say so and link the documents (no guessing)

One Gemini call returns the standard rules, each with an exact quote and the page/block it came from.
The verifier re-opens that page/block and checks the quote, the value and the arithmetic.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from . import config
from . import tender_source as T

LOCAL_PACKS = {"769674-2026": "769674-2026", "26PROC020181047": "backup-OLPA-26PROC020181047"}

# keywords that find the pages holding each rule in a long tender PDF
PAGE_HINTS = [
    r"κύκλο[υς]? εργασιών", r"εγγύηση συμμετοχής|εγγυητική επιστολή συμμετοχής", r"ISO\s*\d{4,5}",
    r"Τεχνική και επαγγελματική ικανότητα|συναφή έργα|παρόμοια έργα|έργα αντίστοιχου",
    r"Ομάδα Έργου|Υπεύθυνος Έργου|Project Manager", r"εκτιμώμενη αξία|προϋπολογισμός .{0,40}ανέρχεται",
]

_Q = {"type": ["string", "null"], "description": "Exact words copied from ONE marked page/block that state this rule."}
_R = {"type": ["string", "null"], "description": "The marker of that page/block, e.g. p33 or C2."}
SCHEMA = {
    "type": "object",
    "properties": {
        "budget": {"type": "object", "properties": {
            "amount_eur": {"type": ["number", "null"], "description": "Initial estimated value EXCLUDING VAT and EXCLUDING options."},
            "quote": _Q, "ref": _R}, "required": ["amount_eur", "quote", "ref"]},
        "turnover": {"type": "object", "properties": {
            "min_eur": {"type": ["number", "null"], "description": "Minimum turnover in EUR; compute it if stated as % of the budget."},
            "basis": {"type": ["string", "null"], "enum": ["total", "average", None], "description": "total over the years, or yearly average"},
            "years": {"type": ["string", "null"]},
            "percent_of_budget": {"type": ["number", "null"]},
            "quote": _Q, "ref": _R}, "required": ["min_eur", "basis", "years", "percent_of_budget", "quote", "ref"]},
        "experience": {"type": "object", "properties": {
            "summary": {"type": ["string", "null"], "description": "One plain English sentence: what past projects are required."},
            "min_projects": {"type": ["integer", "null"]},
            "quote": _Q, "ref": _R}, "required": ["summary", "min_projects", "quote", "ref"]},
        "iso": {"type": "object", "properties": {
            "standards": {"type": "array", "items": {"type": "string"}, "description": "Standard numbers only, e.g. 9001, 27001."},
            "quote": _Q, "ref": _R}, "required": ["standards", "quote", "ref"]},
        "team": {"type": "object", "properties": {
            "roles": {"type": "array", "items": {"type": "string"}, "description": "Required team roles in plain English, with counts."},
            "quote": _Q, "ref": _R}, "required": ["roles", "quote", "ref"]},
        "guarantee": {"type": "object", "properties": {
            "amount_eur": {"type": ["number", "null"]}, "percent": {"type": ["number", "null"]},
            "quote": _Q, "ref": _R}, "required": ["amount_eur", "percent", "quote", "ref"]},
    },
    "required": ["budget", "turnover", "experience", "iso", "team", "guarantee"],
}

SYSTEM = (
    "You read Greek public-procurement documents and extract the bidder eligibility rules for a small company. "
    "Use only the marked pages/blocks. For each rule copy one exact quote from ONE page/block and give its marker. "
    "Use null when a rule is not stated. Budget means the initial value excluding VAT and options (TED's procedure "
    "value may include options; the lot value or the document's own figure is usually the initial one)."
)


# ---- sources -----------------------------------------------------------------------------------

def gather(notice_id: str) -> dict:
    """Returns {"kind": "pack"|"ted"|"none", "units": [(ref, label, text, src)], "note"}."""
    if notice_id in LOCAL_PACKS:
        pack = LOCAL_PACKS[notice_id]
        pages = T.pack_pages(pack)
        pick: list[int] = []
        for pat in PAGE_HINTS:
            scored = sorted(((len(re.findall(pat, T.norm(p), re.I)), i + 1) for i, p in enumerate(pages)), key=lambda x: (-x[0], x[1]))
            pick += [pg for n, pg in scored[:2] if n]
        pick = sorted(set(pick))[:12]
        units = [(f"p{pg}", f"Tender document, PDF p{pg}", T.pack_page(pack, pg), {"kind": "pack", "pack": pack, "page": pg}) for pg in pick]
        return {"kind": "pack", "units": units, "note": f"Read from the tender document ({len(units)} relevant pages)."}
    from . import ted

    xml, src = ted.notice_xml(notice_id)
    if not xml:
        return {"kind": "none", "units": [], "note": "The TED notice could not be fetched."}
    blocks = T.ted_blocks_from_xml(xml)
    units = [(k, b["label"], b["text"], {"kind": "ted", "pub": notice_id, "block": k}) for k, b in blocks.items()]
    crit = [b["text"] for k, b in blocks.items() if k.startswith("C")]
    if crit and all(len(T.norm(t)) < 80 for t in crit):
        return {"kind": "none", "units": units, "note": "This notice only says the criteria are \"as stated in the tender document\"; the rules aren't on TED."}
    if not any(k.startswith("C") for k in blocks):
        return {"kind": "none", "units": units, "note": "This notice doesn't publish its selection criteria on TED; they are only in the tender documents."}
    return {"kind": "ted", "units": units, "note": f"Read from the TED notice's own text ({sum(k.startswith('C') for k in blocks)} selection criteria)."}


def context(units: list) -> str:
    return "\n".join(f"---{'PDF ' if ref.startswith('p') else 'TED '}{ref}---\n{label}\n{text}" for ref, label, text, _ in units)


def gemini_reader(ctx: str) -> dict:
    from google.genai import types

    from . import gemini

    r = gemini.client().models.generate_content(
        model=gemini.MODEL, contents=f"MARKED PAGES/BLOCKS:\n{ctx}",
        config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0, response_mime_type="application/json",
                                           response_json_schema=SCHEMA, thinking_config=gemini.fast_thinking()))
    try:
        return json.loads(r.text or "{}")
    except json.JSONDecodeError:
        return {}


# ---- read + build verifiable claims ------------------------------------------------------------

def _gr(n: float) -> list[str]:
    w = f"{n:,.0f}"
    return [w.replace(",", "."), w.replace(",", ""), w]


def read(notice_id: str, reader: Callable[[str], dict] | None = None) -> dict:
    """Extract rules + the claims the verifier will grade. Does not touch the profile."""
    g = gather(notice_id)
    if g["kind"] == "none":
        return {"notice_id": notice_id, "source": g, "rules": {}, "claims": []}
    if reader is None:
        from . import gemini

        ok, why = gemini.configured()
        if not ok:
            return {"notice_id": notice_id, "source": {**g, "note": f"Gemini not configured ({why}); rules not read."}, "rules": {}, "claims": []}
        reader = gemini_reader
    raw = reader(context(g["units"])) or {}
    by_ref = {ref: (label, src) for ref, label, _, src in g["units"]}
    rules: dict[str, dict] = {}
    claims: list[dict] = []

    def src_of(ref: str | None):
        ref = (ref or "").strip().lstrip("-").replace("PDF ", "").replace("TED ", "")
        hit = by_ref.get(ref)
        if hit is None and g["kind"] == "pack" and re.fullmatch(r"p\d+", ref):
            # Any page of the same PDF is a valid citation: the verifier re-opens it.
            pack = g["units"][0][3]["pack"]
            pg = int(ref[1:])
            if 1 <= pg <= len(T.pack_pages(pack)):
                hit = (f"Tender document, PDF p{pg}", {"kind": "pack", "pack": pack, "page": pg})
                by_ref[ref] = hit
        return ref, hit

    for key, item in raw.items():
        if not isinstance(item, dict):
            continue
        ref, hit = src_of(item.get("ref"))
        item = {**item, "ref": ref, "label": hit[0] if hit else None}
        rules[key] = item
        if not item.get("quote") or not hit:
            continue
        must = []
        if key == "budget" and item.get("amount_eur"):
            must = [_gr(item["amount_eur"])]
        elif key == "guarantee" and item.get("amount_eur"):
            qn = T.norm(item["quote"])
            stated_amount = re.search(r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?\s*€|\d+(?:,\d{2})?\s*€|ευρώ", qn)
            if stated_amount or not item.get("percent"):
                must = [_gr(item["amount_eur"])]          # the quote states an amount: it must be this one
            else:
                must = [[f"{item['percent']:g}%".replace(".", ",")]]   # only a % is stated: the arithmetic check covers the amount
        elif key == "turnover" and item.get("percent_of_budget"):
            must = [[f"{item['percent_of_budget']:g}%", f"({item['percent_of_budget']:g}%)"]]
        elif key == "turnover" and item.get("min_eur"):
            must = [_gr(item["min_eur"])]
        elif key == "experience" and item.get("min_projects"):
            must = [[f"({item['min_projects']})", f" {item['min_projects']} "]]
        elif key == "iso":
            must = [[s] for s in item.get("standards") or []]
        claims.append({
            "claim_id": f"rule:{key}", "notice_id": notice_id, "kind": "rule_quote", "origin": "check_eligibility", "actor": "gemini",
            "statement": f"{key}: {json.dumps({k: v for k, v in item.items() if k not in ('quote', 'ref', 'label')}, ensure_ascii=False)}",
            "citation": _citation(notice_id, hit[1], hit[0], item["quote"]),
            "check": {"source": hit[1], "quote": item["quote"], "must": must},
            "value": item.get("amount_eur") or item.get("min_eur") or item.get("min_projects") or item.get("standards"),
            "required": True,
        })
    # arithmetic: % of budget must give the stated amount
    b = (rules.get("budget") or {}).get("amount_eur")
    for key, pct_field, amt_field in (("guarantee", "percent", "amount_eur"), ("turnover", "percent_of_budget", "min_eur")):
        r = rules.get(key) or {}
        if b and r.get(pct_field) and r.get(amt_field):
            claims.append({
                "claim_id": f"rule:{key}:arith", "notice_id": notice_id, "kind": "rule_arith", "origin": "check_eligibility", "actor": "gemini",
                "statement": f"{key}: {r[pct_field]:g}% of budget €{b:,.0f} = €{r[amt_field]:,.0f}",
                "citation": _citation(notice_id, by_ref[r["ref"]][1], by_ref[r["ref"]][0], r.get("quote")) if r.get("ref") in by_ref else None,
                "check": {"pct": r[pct_field], "base": b, "pct_source": by_ref[r["ref"]][1] if r.get("ref") in by_ref else None, "pct_quote": r.get("quote")},
                "value": r[amt_field], "required": True,
            })
    return {"notice_id": notice_id, "source": g, "rules": rules, "claims": claims}


def _citation(notice_id: str, src: dict, label: str, quote: str | None) -> dict:
    if src["kind"] == "pack":
        pg = src["page"]
        printed = T.printed_page(pg) if src["pack"] == "769674-2026" else pg
        url = f"/api/tenders/{notice_id}/rfp#page={pg}"
        return {"section": "tender document", "pdf_page": pg, "printed_page": printed, "quoted_span": quote, "url": url, "source": src}
    return {"section": label, "pdf_page": None, "printed_page": None, "quoted_span": quote,
            "url": f"https://ted.europa.eu/en/notice/-/detail/{notice_id}", "source": src}


# ---- compare with the profile ------------------------------------------------------------------

def compare(rules: dict, profile: dict) -> list[dict]:
    out = []

    def add(rid, title, status, notes, item):
        cit = None
        if item and item.get("quote"):
            cit = {"section": item.get("label") or "", "quoted_span": item.get("quote"), "ref": item.get("ref")}
        out.append({"id": rid, "title": title, "status": status, "notes": notes, "citation": cit or {"section": "not stated"}})

    t = rules.get("turnover") or {}
    tv = profile.get("turnover_2023_2025_total_eur")
    if t.get("min_eur"):
        need, basis = float(t["min_eur"]), t.get("basis") or "total"
        have = (tv / 3) if (tv is not None and basis == "average") else tv
        st = "unclear" if tv is None else ("meets" if have >= need else "missing")
        add("turnover", f"Turnover ({'yearly average' if basis == 'average' else '3-year total'}) ≥ €{need:,.0f}", st,
            f"Tender: {t.get('years') or ''} {basis}. You: " + ("not given." if tv is None else f"€{have:,.0f} {'per year on average' if basis == 'average' else 'total'}."), t)
    else:
        add("turnover", "Turnover", "unclear", "No turnover rule found in the text we could read.", t)

    e = rules.get("experience") or {}
    projects = profile.get("public_sector_projects_last_5y")
    none = projects is not None and re.fullmatch(r"\s*(none|no|κανένα|-)\s*\.?\s*", str(projects), re.I)
    if e.get("summary"):
        st = "unclear" if projects is None else ("missing" if none else "unclear")
        add("experience", "Similar past projects", st, f"Required: {e['summary']} " + ("Compare with your projects." if st == "unclear" and projects else ""), e)

    iso = rules.get("iso") or {}
    req = [s for s in iso.get("standards") or []]
    if req:
        held = {re.sub(r"\D", "", c)[:5] for c in profile.get("certificates") or []}
        held |= {h[:4] for h in held}
        missing = [s for s in req if re.sub(r"\D", "", s)[:5] not in held and re.sub(r"\D", "", s)[:4] not in held]
        add("iso", f"ISO certificates ({len(req)})", "meets" if not missing else "missing",
            ("Missing: " + ", ".join("ISO " + m for m in missing)) if missing else "You hold them all.", iso)

    tm = rules.get("team") or {}
    if tm.get("roles"):
        add("team", "Minimum project team", "unclear", "Named team required: " + "; ".join(tm["roles"]), tm)

    g = rules.get("guarantee") or {}
    if g.get("amount_eur") or g.get("percent"):
        amt = f"€{g['amount_eur']:,.0f}" if g.get("amount_eur") else f"{g['percent']:g}% of the budget"
        add("guarantee", "Participation guarantee", "unclear", f"A bank guarantee of {amt} must be lodged with the bid.", g)
    return out


def verdict(rows: list[dict]) -> str:
    core = [r for r in rows if r["id"] in ("turnover", "experience", "iso")]
    if any(r["status"] == "missing" for r in core):
        return "not_eligible"
    if core and all(r["status"] == "meets" for r in core):
        return "eligible"
    return "unclear"


# ---- measured against the hand-made ΚτΠ index ---------------------------------------------------

def agreement_with_index(rules: dict, notice_id: str = "769674-2026") -> dict:
    """Compare the generic reader with requirements.json (a human answer key, used only for this score)."""
    req = T.requirements(notice_id)
    sel = {c["id"]: c for c in req["selection_criteria"]}
    guar = next(d for d in req["documents"] if d["id"] == "participation_guarantee")
    want_iso = {"9001", "20000", "27001", "27701", "22301", "37001"}
    got_iso = {re.sub(r"\D", "", s)[:5] for s in (rules.get("iso") or {}).get("standards") or []}
    checks = {
        "budget": ((rules.get("budget") or {}).get("amount_eur"), req["notice"]["value"]["initial_ex_vat"]),
        "turnover": ((rules.get("turnover") or {}).get("min_eur"), sel["turnover"]["computed_threshold_eur"]),
        "turnover basis": ((rules.get("turnover") or {}).get("basis"), "total"),
        "escrow projects": ((rules.get("experience") or {}).get("min_projects"), 5),
        "ISO set": (sorted(got_iso), sorted(want_iso)),
        "guarantee": ((rules.get("guarantee") or {}).get("amount_eur"), guar["amount_eur"]),
    }
    rows = []
    for name, (got, want) in checks.items():
        ok = (abs(float(got) - float(want)) < 0.5) if isinstance(want, (int, float)) and isinstance(got, (int, float)) else got == want
        rows.append({"rule": name, "generic": got, "hand_index": want, "agree": bool(ok)})
    return {"agree": sum(r["agree"] for r in rows), "total": len(rows), "rows": rows}
