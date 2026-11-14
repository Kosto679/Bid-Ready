"""Live extraction on a tender nobody annotated (extra #5: the ΟΛΠΑ backup, ΑΔΑΜ 26PROC020181047).

No requirements.json, no answer key. For each field:
  1. find candidate pages by keyword (deterministic retrieval over the PDF's page text),
  2. Gemini reads those pages and returns value + exact quote + PDF page,
  3. the verifier checks what can be checked without an answer key:
     - the quote is really on the cited page, and the value appears in it (quote_supports_value),
     - figures that depend on each other agree: guarantee = stated % x budget (arithmetic).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable

from . import config, verifier
from . import tender_source as T

PACKS = {
    "26PROC020181047": {
        "pack": "backup-OLPA-26PROC020181047",
        "pdf": "docs/26PROC020181047.pdf",
        "title": "ΟΛΠΑ Α.Ε. (Patras Port): Σχεδιασμός και ανάπτυξη νέας πλατφόρμας εφαρμογών",
    }
}

FIELDS = [
    {"id": "initial_value_ex_vat_eur", "type": "num", "pat": r"εκτιμώμενη αξία|προϋπολογισμ",
     "q": "What is the contract's estimated value (budget) EXCLUDING VAT and EXCLUDING any options or extensions, in EUR? Number only."},
    {"id": "participation_guarantee_eur", "type": "num", "pat": r"εγγύηση συμμετοχής|εγγυητική επιστολή συμμετοχής",
     "q": "What amount must the participation guarantee (εγγύηση συμμετοχής) be, in EUR? Number only."},
    {"id": "submission_deadline", "type": "datetime", "pat": r"καταληκτική ημερομηνία",
     "q": "What is the deadline for submitting offers? Answer as YYYY-MM-DDTHH:MM (Europe/Athens)."},
    {"id": "iso_standards", "type": "list", "pat": r"ISO\s*\d{4,5}",
     "q": "Which ISO standards must bidders hold? Answer as a comma-separated list of the standard numbers only, e.g. 9001, 27001."},
]

SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "quote": {"type": ["string", "null"], "description": "Exact words copied from ONE page that state the answer."},
        "pdf_page": {"type": ["integer", "null"], "description": "The PDF page number (from the ---PDF pN--- marker) the quote is on."},
    },
    "required": ["value", "quote", "pdf_page"],
}

SYSTEM = ("You extract facts from a Greek public-procurement notice. Answer only from the pages given. Copy the quote "
          "exactly from a single page and give that page's number from its ---PDF pN--- marker. If the pages don't state it, return nulls.")


def candidate_pages(pack: str, pat: str, k: int = 3) -> list[int]:
    pages = T.pack_pages(pack)
    scored = [(len(re.findall(pat, T.norm(p), re.I)), i + 1) for i, p in enumerate(pages)]
    return [pg for n, pg in sorted(scored, key=lambda x: (-x[0], x[1])) if n][:k]


def gemini_reader(question: str, context: str) -> dict:
    from google.genai import types

    from . import gemini

    r = gemini.client().models.generate_content(
        model=gemini.MODEL, contents=f"PAGES:\n{context}\n\nQUESTION: {question}",
        config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0, response_mime_type="application/json",
                                           response_json_schema=SCHEMA, thinking_config=gemini.fast_thinking()))
    try:
        return json.loads(r.text or "{}")
    except json.JSONDecodeError:
        return {}


def parse(raw: Any, kind: str) -> Any:
    from .evals import parse_answer

    if kind == "list":
        nums = re.findall(r"\d{4,5}(?:-\d)?", str(raw or ""))
        return sorted(set(n.split("-")[0] for n in nums)) or None
    return parse_answer(raw, kind)


def run(notice_id: str = "26PROC020181047", reader: Callable[[str, str], dict] | None = None) -> dict:
    meta = PACKS[notice_id]
    pack = meta["pack"]
    if reader is None:
        from . import gemini

        ok, why = gemini.configured()
        if not ok:
            raise gemini.NotConfigured(why)
        reader = gemini_reader
    run_id = "live_" + datetime.now(config.ATHENS).strftime("%Y%m%d_%H%M%S")
    found: dict[str, dict] = {}
    claims: list[dict] = []
    for f in FIELDS:
        pages = candidate_pages(pack, f["pat"])
        ctx = "\n".join(f"---PDF p{p}---\n{T.pack_page(pack, p)}" for p in pages)
        try:
            ans = reader(f["q"], ctx) or {}
        except Exception as e:
            ans = {"error": f"{type(e).__name__}: {e}"}
        value = parse(ans.get("value"), f["type"])
        found[f["id"]] = {"value": value, "raw": ans.get("value"), "quote": ans.get("quote"), "pdf_page": ans.get("pdf_page"),
                          "searched_pages": pages, "error": ans.get("error")}
        claims.append(_claim(notice_id, pack, f, value, ans))

    # Cross-check: guarantee = the percentage its own clause states x the extracted budget.
    g, b = found["participation_guarantee_eur"], found["initial_value_ex_vat_eur"]
    if g["value"] is not None and b["value"] is not None and g["pdf_page"]:
        claims.append({
            "claim_id": "live:arith:guarantee", "notice_id": notice_id, "kind": "arithmetic_pct", "origin": "live_extract",
            "actor": "gemini", "statement": f"Guarantee €{g['value']:,.0f} = the % stated in its clause × budget €{b['value']:,.0f}",
            "citation": _cit(notice_id, g["pdf_page"], "guarantee clause"),
            "check": {"pack": pack, "pdf_page": g["pdf_page"], "quote": g["quote"], "base": b["value"]},
            "value": g["value"],
        })

    receipts = verifier.verify(run_id, claims)
    by_id = {r["intent"]["claim_id"]: r for r in receipts}
    for fid, row in found.items():
        r = by_id.get(f"live:{fid}")
        row["status"] = r["status"] if r else None
        row["reason"] = r["reason"] if r else None
    arith = by_id.get("live:arith:guarantee")
    result = {"run_id": run_id, "notice_id": notice_id, "title": meta["title"], "fields": found,
              "arithmetic": {"status": arith["status"], "observed": arith["independent_check"].get("observed"), "reason": arith["reason"]} if arith else None,
              "receipts": receipts, "pdf_url": f"/api/tenders/{notice_id}/rfp"}
    d = config.OUT_DIR / "live"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{run_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return result


def _cit(notice_id: str, pg: Any, section: str) -> dict:
    pg = pg if isinstance(pg, int) else None
    return {"section": section, "pdf_page": pg, "printed_page": pg, "url": f"/api/tenders/{notice_id}/rfp#page={pg}" if pg else None}


def _claim(notice_id: str, pack: str, f: dict, value: Any, ans: dict) -> dict:
    return {
        "claim_id": f"live:{f['id']}", "notice_id": notice_id, "kind": "quote_supports_value", "origin": "live_extract",
        "actor": "gemini", "statement": f"{f['id']} = {value}",
        "citation": _cit(notice_id, ans.get("pdf_page"), f["id"]),
        "check": {"pack": pack, "pdf_page": ans.get("pdf_page"), "quote": ans.get("quote"), "type": f["type"]},
        "value": value,
        "tool_call": {"name": "gemini_read_pages", "arguments": {"field": f["id"]}},
    }
