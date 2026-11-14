"""ΚΗΜΔΗΣ (Greek central procurement register) open-data API: filtered scan, records, tender documents.

API: https://cerpp.eprocurement.gov.gr/khmdhs-opendata (no key). Every Greek public tender is here, including
ones never sent to TED. Each notice has an ΑΔΑΜ id (e.g. 26PROC020137847); /notice/attachment/{ΑΔΑΜ}
serves its tender document. Documents are downloaded once into data/tender-demo/khmdhs-cache/{ΑΔΑΜ}/ and
their page text extracted, so the generic rule reader and the verifier can cite and re-open PDF pages.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from . import config

BASE = "https://cerpp.eprocurement.gov.gr/khmdhs-opendata"
CACHE = "khmdhs-cache"  # under data/tender-demo/
ADAM_RE = re.compile(r"^\d{2}PROC\d{9}$")


def is_adam(s: str) -> bool:
    return bool(ADAM_RE.match(s or ""))


def _dir(adam: str) -> Path:
    return config.DATA_DIR / CACHE / adam


def pack_name(adam: str) -> str:
    """Folder name for tender_source.pack_pages()."""
    return f"{CACHE}/{adam}"


def _dt(d: str | datetime) -> str:
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d %H:%M")
    return d if " " in d else f"{d[:10]} 00:00"


def search(criteria: dict, page: int = 0, timeout: float = 30) -> dict:
    with httpx.Client(timeout=timeout) as c:
        r = c.post(f"{BASE}/notice", params={"page": page}, json=criteria)
        if r.status_code == 404:  # the API answers 404 when nothing matches
            return {"content": [], "totalElements": 0, "totalPages": 0}
        r.raise_for_status()
        return r.json()


def normalize(rec: dict) -> dict:
    sys_nums = [s.get("systemicNumber") for s in rec.get("systemicNumbers") or [] if s.get("systemicNumber")]
    return {
        "adam": rec.get("referenceNumber"),
        "title": rec.get("title"),
        "buyer_name": (rec.get("organization") or {}).get("value"),
        "buyer_vat": rec.get("organizationVatNumber"),
        "deadline": rec.get("finalSubmissionDate"),
        "cost_ex_vat": rec.get("totalCostWithoutVAT"),
        "option_right": (rec.get("optionRight") or {}).get("value") if isinstance(rec.get("optionRight"), dict) else rec.get("optionRight"),
        "notice_type": (rec.get("noticeType") or {}).get("value"),
        "procedure": (rec.get("typeOfProcedure") or {}).get("value"),
        "nuts": (rec.get("nutsCode") or {}).get("key"),
        "esidis": sys_nums,
        "cancelled": rec.get("cancelled"),
        "url": f"{BASE}/notice/attachment/{rec.get('referenceNumber')}",
    }


def scan(cpv_codes: list[str] | None = None, deadline_from: str | datetime | None = None, deadline_to: str | datetime | None = None,
         cost_from: float | None = None, cost_to: float | None = None, title: str | None = None, max_pages: int = 3) -> dict:
    """Filtered search over open notices. CPV codes must be full codes with check digit (72000000-5)."""
    crit: dict[str, Any] = {}
    if cpv_codes:
        crit["cpvItems"] = cpv_codes
    if deadline_from:
        crit["finalDateFrom"] = _dt(deadline_from)
    if deadline_to:
        crit["finalDateTo"] = _dt(deadline_to)
    if cost_from is not None:
        crit["totalCostFrom"] = cost_from
    if cost_to is not None:
        crit["totalCostTo"] = cost_to
    if title:
        crit["title"] = title[:200]
    out, total, pages = [], None, 0
    for p in range(max_pages):
        d = search(crit, page=p)
        total = d.get("totalElements", total)
        pages = d.get("totalPages", 1)
        out += [normalize(x) for x in d.get("content", [])]
        if p + 1 >= pages:
            break
    out = [n for n in out if not n["cancelled"]]
    return {"criteria": crit, "total": total, "notices": out}


def record(adam: str) -> dict | None:
    """One notice by ΑΔΑΜ (cached on disk)."""
    p = _dir(adam) / "record.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    d = search({"referenceNumber": adam})
    items = d.get("content") or []
    if not items:
        return None
    rec = normalize(items[0])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def document(adam: str, timeout: float = 60) -> Path | None:
    """Download the notice's tender document once. Returns the cached PDF path, or None if it isn't a PDF."""
    pdf = _dir(adam) / "document.pdf"
    if pdf.exists() and pdf.stat().st_size > 1000:
        return pdf
    with httpx.Client(timeout=timeout, follow_redirects=True) as c:
        r = c.get(f"{BASE}/notice/attachment/{adam}")
        r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        return None
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(r.content)
    return pdf


def pages(adam: str) -> list[str]:
    """Per-page text of the tender document (extracted once with pypdf, cached as text/pages.json)."""
    out = _dir(adam) / "text" / "pages.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    pdf = document(adam)
    if pdf is None:
        return []
    from pypdf import PdfReader

    texts = []
    for pg in PdfReader(str(pdf)).pages:
        try:
            texts.append(pg.extract_text() or "")
        except Exception:
            texts.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    return texts


# ---- TED -> ΚΗΜΔΗΣ -------------------------------------------------------------------------------

def _esidis_from_ted(xml: str) -> set[str]:
    """ΕΣΗΔΗΣ system numbers appear in TED document links, e.g. .../actSearch/resources/search/589064."""
    nums = set(re.findall(r"(?:search/|systemic[^0-9]{0,20}|α/α\s*)(\d{5,7})\b", xml))
    nums |= set(re.findall(r"ΕΣΗΔΗΣ[^0-9]{0,40}(\d{5,7})\b", xml))
    return nums


def _deadline_from_ted(xml: str) -> str | None:
    m = re.search(r"<cac:TenderSubmissionDeadlinePeriod>.*?<cbc:EndDate>(\d{4}-\d{2}-\d{2})", xml, re.S)
    return m.group(1) if m else None


def _values_from_ted(xml: str) -> list[float]:
    """Procedure value first, then up to 3 lot values (ΚΗΜΔΗΣ stores the cost excl. VAT and options)."""
    vals = [float(v) for v in re.findall(r"EstimatedOverallContractAmount[^>]*>([\d.]+)<", xml)]
    return list(dict.fromkeys(vals))[:4]


def _fold(s: str) -> str:
    """Lowercase and strip Greek accents, so 'ΔΡΑΣΕΙΣ ΨΗΦΙΑΚΟΥ' matches 'Δράσεις Ψηφιακού'."""
    import unicodedata

    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").replace("ς", "σ")


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[0-9a-zα-ω]{4,}", _fold(s))}


def title_similarity(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def _prefer(cands: list[dict]) -> dict:
    """Among duplicates (summary vs full notice), prefer the full tender notice, then the latest ΑΔΑΜ."""
    rank = {"Διακήρυξη": 0, "Προκήρυξη": 1}
    return sorted(cands, key=lambda c: (rank.get(c.get("notice_type"), 2), -int(re.sub(r"\D", "", c["adam"] or "0") or 0)))[0]


def _gemini_pick(ted_title: str, buyer: str, cands: list[dict]) -> int | None:
    """Gemini chooses which candidate is the same tender (or none). Code has already required same deadline and value."""
    from . import gemini

    if not gemini.configured()[0] or not cands:
        return None
    from google.genai import types

    listing = "\n".join(f"{i}: {c['title']} | buyer: {c['buyer_name']}" for i, c in enumerate(cands))
    schema = {"type": "object", "properties": {"index": {"type": ["integer", "null"]}}, "required": ["index"]}
    r = gemini.client().models.generate_content(
        model=gemini.MODEL,
        contents=f"TED notice: {ted_title} | buyer: {buyer}\n\nCandidates from the Greek register:\n{listing}\n\n"
                 "Which candidate is the same tender? Return its index, or null if none clearly is.",
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json", response_json_schema=schema,
                                           thinking_config=gemini.fast_thinking()))
    try:
        i = json.loads(r.text or "{}").get("index")
    except json.JSONDecodeError:
        return None
    return i if isinstance(i, int) and 0 <= i < len(cands) else None


def match_ted(publication_number: str, use_gemini: bool = True) -> dict | None:
    """Find the ΚΗΜΔΗΣ record for a TED notice. Candidates must close the same day and have the same value
    (TED procedure or lot value = ΚΗΜΔΗΣ cost excl. VAT, ±1%). Then, in order: same ΕΣΗΔΗΣ number; one
    clearly similar title; Gemini's pick among the candidates. Cached. Returns {"adam", "how", "record"} or None."""
    cache = config.DATA_DIR / CACHE / "ted-matches.json"
    known = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    if known.get(publication_number):
        return known[publication_number]
    from . import ted

    xml, _ = ted.notice_xml(publication_number)
    if not xml:
        return None
    nums, day, values = _esidis_from_ted(xml), _deadline_from_ted(xml), _values_from_ted(xml)
    meta = (ted.get_notice(publication_number, run_id="match").get("notice") or {})
    ted_title, buyer = meta.get("title") or "", meta.get("buyer_name") or ""
    hit = None
    if day:
        cands: dict[str, dict] = {}
        for v in values or [None]:
            kw = {"cost_from": round(v * 0.99, 2), "cost_to": round(v * 1.01, 2)} if v else {}
            for c in scan(deadline_from=f"{day} 00:00", deadline_to=f"{day} 23:59", max_pages=2, **kw)["notices"]:
                cands[c["adam"]] = c
        pool = list(cands.values()) if values else []
        same_esidis = [c for c in pool if nums & set(c["esidis"])]
        # title: accept one clear winner (>= 0.6 and 0.25 ahead of any differently-titled runner-up)
        sims = sorted(((title_similarity(ted_title, c["title"]), c) for c in pool), key=lambda x: -x[0])
        best = [c for s, c in sims if sims and s == sims[0][0]]
        runner = next((s for s, c in sims if re.sub(r"\W", "", c["title"].lower()) != re.sub(r"\W", "", best[0]["title"].lower())), 0.0) if best else 0.0
        clear_title = bool(best) and sims[0][0] >= 0.6 and sims[0][0] - runner >= 0.25
        if same_esidis:
            c = _prefer(same_esidis)
            hit = {"adam": c["adam"], "how": f"ΕΣΗΔΗΣ number {sorted(nums & set(c['esidis']))[0]}, deadline {day}, same value", "record": c}
        elif clear_title:
            c = _prefer(best)
            hit = {"adam": c["adam"], "how": f"same deadline {day}, same value and title", "record": c}
        elif pool and use_gemini:
            i = _gemini_pick(ted_title, buyer, pool)
            if i is not None:
                c = pool[i]
                hit = {"adam": c["adam"], "how": f"Gemini's pick among {len(pool)} with the same deadline {day} and value", "record": c}
    known[publication_number] = hit
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
    return hit
