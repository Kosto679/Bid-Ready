"""Verified turnover rules per tender, so the shortlist score can use a tender's real rule.

Only a rule the verifier has re-read on the tender's own page/block and marked VERIFIED is stored.
Never written from requirements.json directly.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config


def _path() -> Path:
    return config.OUT_DIR / "rule_cache.json"


def load_all() -> dict[str, dict]:
    p = _path()
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get(notice_id: str) -> dict | None:
    return load_all().get(notice_id)


def save_turnover(notice_id: str, min_eur: float, basis: str, source: str) -> None:
    """basis: 'total' (sum of the years) or 'average' (per year)."""
    data = load_all()
    data[notice_id] = {"min_eur": float(min_eur), "basis": basis if basis in ("total", "average") else "total",
                       "source": source, "saved": config.ts_athens()}
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def save_from_receipts(notice_id: str, receipts: list[dict], rules: dict | None = None) -> None:
    """Store the turnover rule if its receipt is VERIFIED. Handles the ΚτΠ claim and generic rule claims."""
    for r in receipts:
        cid = (r.get("intent") or {}).get("claim_id")
        if r.get("status") != "VERIFIED":
            continue
        if cid == "turnover_threshold":
            obs = (r.get("independent_check") or {}).get("observed") or {}
            if obs.get("turnover_3y_total_min_eur"):
                save_turnover(notice_id, obs["turnover_3y_total_min_eur"], "total", "tender PDF (§2.2.5), verified")
        elif cid == "rule:turnover" and rules:
            t = rules.get("turnover") or {}
            if t.get("min_eur"):
                save_turnover(notice_id, t["min_eur"], t.get("basis") or "total", "read from the tender, verified")
