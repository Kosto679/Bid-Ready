"""Read the actual tender text, page by page. This is what the verifier re-opens.

text/pages.json is a list where index i holds PDF page i+1 of the KtP RFP.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from . import config

RFP_PDF_NAME = "RFP_ESCROW_ACCOUNTS_26PROC020137847_ΨΣ8Σ469Η4Σ-ΝΛΘ.pdf"


def notice_dir(notice_id: str) -> Path:
    return config.DATA_DIR / notice_id


def has_local_pack(notice_id: str) -> bool:
    return (notice_dir(notice_id) / "text" / "pages.json").exists()


@lru_cache(maxsize=8)
def _pages(notice_id: str) -> tuple[str, ...]:
    path = notice_dir(notice_id) / "text" / "pages.json"
    return tuple(json.loads(path.read_text(encoding="utf-8")))


def page_text(notice_id: str, pdf_page: int) -> str:
    """Raw text of one PDF page (1-based). Raises FileNotFoundError / IndexError if it cannot be opened."""
    pages = _pages(notice_id)
    if pdf_page < 1 or pdf_page > len(pages) or not pages[pdf_page - 1].strip():
        raise IndexError(f"PDF page {pdf_page} not available for {notice_id}")
    return pages[pdf_page - 1]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def printed_page(pdf_page: int) -> int:
    """KtP RFP: printed page = PDF page - 7 (body pages)."""
    return pdf_page - config.KTP_PAGE_OFFSET


def printed_footer(notice_id: str, pdf_page: int) -> int | None:
    """Read the printed footer 'X - 103' off the page itself."""
    m = re.search(r"(\d{1,3})\s*-\s*103\b", page_text(notice_id, pdf_page))
    return int(m.group(1)) if m else None


def find_span(notice_id: str, pdf_page: int, anchor: str, after: int = 160, before: int = 0) -> str | None:
    """Return a whitespace-normalised quote around `anchor` from the real page, or None."""
    t = norm(page_text(notice_id, pdf_page))
    i = t.find(norm(anchor))
    if i < 0:
        return None
    return t[max(0, i - before): i + len(norm(anchor)) + after].strip()


def span_on_page(notice_id: str, pdf_page: int, span: str) -> bool:
    return norm(span) in norm(page_text(notice_id, pdf_page))


EUR_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})\s*€")


def parse_eur(s: str) -> float:
    """'4.000,00' -> 4000.0 (Greek number format)."""
    return float(s.replace(".", "").replace(",", "."))


def amounts_after(notice_id: str, pdf_page: int, anchor: str, window: int = 600) -> list[float]:
    """Euro amounts that appear within `window` chars after `anchor` on the page."""
    t = norm(page_text(notice_id, pdf_page))
    i = t.find(norm(anchor))
    if i < 0:
        return []
    chunk = t[i: i + window]
    return [parse_eur(m.group(1) + "," + m.group(2)) for m in EUR_RE.finditer(chunk)]


@lru_cache(maxsize=8)
def pack_pages(pack: str) -> tuple[str, ...]:
    """Per-page text for any tender pack folder under data/tender-demo/: text/pages.json, or a
    pdftotext dump in text/*.txt with form feeds between pages. Index i holds PDF page i+1."""
    d = config.DATA_DIR / pack / "text"
    if (d / "pages.json").exists():
        return tuple(json.loads((d / "pages.json").read_text(encoding="utf-8")))
    for f in sorted(d.glob("*.txt")):
        txt = f.read_text(encoding="utf-8")
        if "\f" in txt:
            return tuple(txt.split("\f"))
    raise FileNotFoundError(f"no per-page text in {d}")


def pack_page(pack: str, pdf_page: int) -> str:
    pages = pack_pages(pack)
    if pdf_page < 1 or pdf_page > len(pages) or not pages[pdf_page - 1].strip():
        raise IndexError(f"PDF page {pdf_page} not available in {pack}")
    return pages[pdf_page - 1]


# ---- TED notice text as citable "blocks" ------------------------------------------------------

SELECTION_TYPES = {
    "slc-suit-reg-prof": "Professional registration", "slc-suit-reg-trade": "Trade registration",
    "slc-stand-turnover": "Turnover", "slc-stand-spec-turnover": "Specific turnover", "slc-stand-ratio": "Financial ratio",
    "slc-stand-insurance": "Insurance", "slc-abil-references-services": "Similar services (references)",
    "slc-abil-references-works": "Similar works (references)", "slc-abil-staff-qualif": "Staff qualifications",
    "slc-abil-qual-control": "Quality assurance (ISO)", "slc-abil-envir-mgmt": "Environmental management",
    "slc-sche-ec-fin": "Economic and financial standing", "slc-sche-tp-ability": "Technical and professional ability",
    # codes seen on live Greek notices
    "slc-stand-other": "Economic standing (other)", "slc-stand-to-avg": "Average turnover",
    "slc-stand-to-spec-avg": "Average specific turnover", "slc-abil-ref-work": "Similar projects (references)",
    "slc-abil-staff-qual": "Team qualifications", "slc-abil-staff-yrly-no-mgmt": "Average staff numbers",
    "slc-sche-qu-cert-indep": "Quality certificates (ISO)", "slc-abil-qual-inst": "Quality assurance (ISO)",
    "slc-abil-subc": "Subcontracting",
}


def ted_blocks_from_xml(xml: str) -> dict[str, dict]:
    """{"C1": {"label", "text"}, ..., "G1": guarantee, "V1": values} from an eForms notice."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml)
    local = lambda el: el.tag.rsplit("}", 1)[-1]
    out: dict[str, dict] = {}
    n = 0
    for el in root.iter():
        if local(el) == "SelectionCriteria":
            code = next((c.text for c in el.iter() if local(c) == "TendererRequirementTypeCode"), "") or ""
            desc = " ".join((c.text or "").strip() for c in el.iter() if local(c) == "Description" and (c.text or "").strip())
            if desc:
                n += 1
                out[f"C{n}"] = {"label": f"TED selection criterion {n}: {SELECTION_TYPES.get(code.strip(), code.strip() or 'criterion')}", "text": desc}
        elif local(el) == "RequiredFinancialGuarantee":
            desc = " ".join((c.text or "").strip() for c in el.iter() if local(c) == "Description" and (c.text or "").strip())
            if desc and "G1" not in out:
                out["G1"] = {"label": "TED guarantee requirement", "text": desc}
    proc, lots = None, []
    for el in root.iter():
        if local(el) in ("ProcurementProject",):
            amt = next((c for c in el if local(c) == "RequestedTenderTotal"), None)
            if amt is not None:
                val = next((c.text for c in amt if local(c) == "EstimatedOverallContractAmount"), None)
                if val:
                    # ProcurementProject directly under the root is the procedure; inside a lot it's the lot
                    lots.append(val)
    if lots:
        proc, lot_vals = lots[0], lots[1:]
        text = f"Procedure estimated value (may include options): {proc} EUR."
        if lot_vals:
            text += " Lot estimated value: " + ", ".join(f"{v} EUR" for v in lot_vals) + "."
        out["V1"] = {"label": "TED estimated values", "text": text}
    return out


def ted_blocks(publication_number: str) -> dict[str, dict]:
    """Re-read the cached notice XML from disk (what the verifier re-opens)."""
    for p in (config.TED_CACHE_DIR / "xml" / f"{publication_number}.xml",
              config.DATA_DIR / publication_number / f"ted-notice-{publication_number}.xml"):
        if p.exists():
            return ted_blocks_from_xml(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no cached TED XML for {publication_number}")


def open_ref(src: dict) -> str:
    """Re-open one citable unit: {"kind": "pack", "pack", "page"} or {"kind": "ted", "pub", "block"}."""
    if src.get("kind") == "pack":
        return pack_page(src["pack"], int(src["page"]))
    if src.get("kind") == "ted":
        b = ted_blocks(src["pub"]).get(src["block"])
        if not b:
            raise IndexError(f"block {src['block']} not in TED notice {src['pub']}")
        return b["text"]
    raise ValueError(f"unknown source kind {src.get('kind')}")


def requirements(notice_id: str) -> dict:
    """Human-curated clause INDEX (what to check, where). Never the sole source of truth."""
    return json.loads((notice_dir(notice_id) / "requirements.json").read_text(encoding="utf-8"))


def rfp_file_rel() -> str:
    return f"docs/ESCROW-ACCOUNTS/{RFP_PDF_NAME}"
