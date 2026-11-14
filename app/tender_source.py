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


def requirements(notice_id: str) -> dict:
    """Human-curated clause INDEX (what to check, where). Never the sole source of truth."""
    return json.loads((notice_dir(notice_id) / "requirements.json").read_text(encoding="utf-8"))


def rfp_file_rel() -> str:
    return f"docs/ESCROW-ACCOUNTS/{RFP_PDF_NAME}"
