"""Paths, timezone and environment for Bid-Ready."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ATHENS = ZoneInfo("Europe/Athens")
DATA_DIR = ROOT / "data" / "tender-demo"
TED_CACHE_DIR = DATA_DIR / "ted-cache"
OUT_DIR = Path(os.environ.get("BIDREADY_OUT", ROOT / "out"))
DB_PATH = Path(os.environ.get("BIDREADY_DB", ROOT / "receipts.db"))

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
TED_TIMEOUT_S = float(os.environ.get("BIDREADY_TED_TIMEOUT", "90"))

# Body PDF page N of the KtP RFP is printed page N-7 (7-page decision preamble).
KTP_PAGE_OFFSET = 7


def offline() -> bool:
    return os.environ.get("BIDREADY_OFFLINE", "0") == "1"


def now_athens() -> datetime:
    override = os.environ.get("BIDREADY_TODAY")  # e.g. 2026-11-15 for reproducible demos/tests
    if override:
        return datetime.fromisoformat(override).replace(tzinfo=ATHENS)
    return datetime.now(ATHENS)


def ts_athens() -> str:
    return datetime.now(ATHENS).isoformat(timespec="seconds")
