"""SQLite receipts + claims store. Every tool calls write_receipt() before it returns.

Statuses: VERIFIED / UNVERIFIED / FAILED (independent check ran), RECORDED (tool call logged, not checked).
Same idempotency_key -> the first receipt is returned unchanged; nothing is written twice.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
  receipt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  intent_json TEXT NOT NULL,
  tool_call_json TEXT NOT NULL,
  tool_response_json TEXT NOT NULL,
  independent_check_json TEXT,
  status TEXT NOT NULL CHECK (status IN ('VERIFIED', 'UNVERIFIED', 'FAILED', 'RECORDED')),
  reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_receipts_run ON receipts(run_id);

CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  claim_json TEXT NOT NULL,
  PRIMARY KEY (run_id, claim_id)
);
"""

STATUSES = {"VERIFIED", "UNVERIFIED", "FAILED", "RECORDED"}


def _db_path() -> Path:
    # Read at call time so tests can point BIDREADY_DB at a temp file.
    import os

    return Path(os.environ.get("BIDREADY_DB", config.DB_PATH))


def connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _row_to_receipt(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "receipt_id": row["receipt_id"],
        "run_id": row["run_id"],
        "idempotency_key": row["idempotency_key"],
        "ts": row["ts"],
        "actor": row["actor"],
        "action": row["action"],
        "intent": json.loads(row["intent_json"]),
        "tool_call": json.loads(row["tool_call_json"]),
        "tool_response": json.loads(row["tool_response_json"]),
        "independent_check": json.loads(row["independent_check_json"]) if row["independent_check_json"] else None,
        "status": row["status"],
        "reason": row["reason"],
    }


def get_by_key(idempotency_key: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
    return _row_to_receipt(row) if row else None


def write_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Insert a receipt, or return the existing one for the same idempotency_key."""
    key = receipt["idempotency_key"]
    existing = get_by_key(key)
    if existing:
        return existing
    status = receipt.get("status", "RECORDED")
    if status not in STATUSES:
        raise ValueError(f"bad status {status}")
    rec = {
        "receipt_id": receipt.get("receipt_id") or f"rcpt_{uuid.uuid4().hex[:12]}",
        "run_id": receipt["run_id"],
        "idempotency_key": key,
        "ts": receipt.get("ts") or config.ts_athens(),
        "actor": receipt.get("actor", "bid-ready-agent"),
        "action": receipt["action"],
        "intent": receipt.get("intent", {}),
        "tool_call": receipt.get("tool_call", {}),
        "tool_response": receipt.get("tool_response", {}),
        "independent_check": receipt.get("independent_check"),
        "status": status,
        "reason": receipt.get("reason"),
    }
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rec["receipt_id"], rec["run_id"], key, rec["ts"], rec["actor"], rec["action"],
                    _dumps(rec["intent"]), _dumps(rec["tool_call"]), _dumps(rec["tool_response"]),
                    _dumps(rec["independent_check"]) if rec["independent_check"] is not None else None,
                    status, rec["reason"],
                ),
            )
        except sqlite3.IntegrityError:
            # Lost a race on the same key: the first writer wins.
            pass
    return get_by_key(key)  # type: ignore[return-value]


def list_receipts(run_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM receipts WHERE run_id = ? ORDER BY ts, rowid", (run_id,)).fetchall()
    return [_row_to_receipt(r) for r in rows]


def save_claims(run_id: str, claims: list[dict[str, Any]]) -> None:
    with connect() as conn:
        for c in claims:
            conn.execute(
                "INSERT OR REPLACE INTO claims VALUES (?,?,?)", (c["claim_id"], run_id, _dumps(c))
            )


def load_claims(run_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT claim_json FROM claims WHERE run_id = ? ORDER BY rowid", (run_id,)).fetchall()
    return [json.loads(r["claim_json"]) for r in rows]


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
