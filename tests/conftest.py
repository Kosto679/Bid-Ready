import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Offline, fresh receipts DB and output dir for every test."""
    monkeypatch.setenv("BIDREADY_OFFLINE", "1")
    monkeypatch.setenv("BIDREADY_DB", str(tmp_path / "receipts.db"))
    monkeypatch.setenv("BIDREADY_TODAY", "2026-11-15")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app import config

    monkeypatch.setattr(config, "OUT_DIR", tmp_path / "out")
    yield


@pytest.fixture
def studio_profile():
    """8-person Athens studio: €350k 3-year total (< €400k), ISO 9001 only, projects answered, none escrow."""
    return {
        "name": "Pixelridge",
        "summary": "8-person software studio in Athens building web apps and data dashboards.",
        "size": 8,
        "location": "Athens, Greece",
        "nuts_or_country": "EL30",
        "cpv_codes": ["72000000", "72200000"],
        "turnover_2023_2025_total_eur": 350_000,
        "certificates": ["ISO 9001"],
        "public_sector_projects_last_5y": "Two small municipal websites (2023, 2025); no escrow-payment systems.",
        "profitable_last_3y": True,
    }
