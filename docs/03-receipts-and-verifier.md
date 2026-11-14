# Receipts and verifier

Build the SQLite table and `write_receipt()` first, in the opening block, before search or scoring. Every tool must write a receipt before it returns.

## SQLite schema

Store one database file, e.g. `receipts.db`.

```sql
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
```

`RECORDED` is only for tool calls that are not yet independently checked (e.g. `find_tenders` logged a search). A pack cannot be `ready` on `RECORDED` or `UNVERIFIED` claims that are required for handover. Eligibility, guarantee, deadline, and pack-file claims must go through `verify` and end as `VERIFIED` or `FAILED`.

Required fields on the JSON object (and in the row): `receipt_id`, `run_id`, `idempotency_key`, `ts`, `actor`, `action`, `intent`, `tool_call`, `tool_response`, `independent_check`, `status`. Use ISO 8601 timestamps with an offset, e.g. `2026-11-15T15:12:11+02:00` (Europe/Athens). Do not use a timestamp after the Sunday 16:30 recording cut-off in fixtures or examples.

## `write_receipt()`

```
write_receipt(receipt: dict) -> dict
```

- If a row with the same `idempotency_key` already exists, return that row unchanged. Do not insert a second receipt and do not write a second file or fire a second side effect.
- Otherwise insert and return the stored receipt.
- `ts` defaults to now in Europe/Athens (`+02:00` in November 2026).

## Statuses

- **VERIFIED** — independent observation from the tender page or the pack file matches the claim.
- **FAILED** — observation conflicts with the claim, or a required file is missing or cannot be read back.
- **UNVERIFIED** — TED or the file source is down, or the citation cannot be re-opened. Not done.

The verifier refuses to mark the run or pack `ready` unless required checks have run. A visible `FAILED` (the guarantee trap) means the pack is handed over as **not ready**, with the receipt included.

## What the verifier must actually re-read

`requirements.json` is a human-curated fixture and clause **index** for TED 769674-2026 (section, `pdf_page`, `doc_page` / printed page, sometimes a quote). Do not grade a claim by comparing the agent to that JSON alone.

For each claim:

1. Take the citation (`section`, `pdf_page`, `printed_page`).
2. Re-open the source file under `data/tender-demo/769674-2026/`. Prefer extracted text with page markers (`text/rfp_compact.txt` uses `---PDF pN---` markers; `text/pages.json` is a per-page array) so you do not need a PDF parser for the demo. If you open the PDF, remember printed page = PDF page minus 7.
3. Extract the quoted span or the numeric value from that page.
4. Compare to the claim. Write `independent_check` with `method` (e.g. `reread_tender_pdf_page`), `source`, `observed`, and `mismatch`.
5. Set `VERIFIED` or `FAILED`. If the page cannot be opened, `UNVERIFIED`.

Also re-read pack files: the letter exists at the claimed path; the `.ics` deadline matches the notice deadline; ZIP entries are present.

## What to check on the ΚτΠ run

At minimum:

- Participation guarantee: naive claim €6,000 (2% of TED headline €300,000) vs observed €4,000 (2% of €200,000 excl. VAT and option) at §2.2.2.1, PDF p27 / printed 20. Must be **FAILED**.
- Turnover rule if claimed: sum of 2023+2024+2025 ≥ €400,000 (200% of €200,000, a 3-year total), §2.2.5, PDF p33 / printed 26. Do not invent a €300,000 vs €400,000 turnover plant — €300,000 is a budget figure, not a turnover threshold.
- Deadline in the `.ics` equals Mon 7 Dec 2026, 14:00 Europe/Athens.
- Eligibility citations that the report lists can be relocated on the stated PDF page.
- Pack files exist and can be read back.

## Example receipt (guarantee trap)

This is a fixture example, not live output. The miss is a known trap: TED shows €300,000, and a naive extractor that trusts that headline computes 2% as €6,000. If asked whether it was arranged, say yes — it is the mistake that headline invites, caught against the PDF page.

```json
{
  "receipt_id": "rcpt_01JK7DEMO",
  "run_id": "run_ktp_escrow",
  "idempotency_key": "check_eligibility:769674-2026:participation_guarantee:v1",
  "ts": "2026-11-15T15:12:11+02:00",
  "actor": "bid-ready-agent",
  "action": "check_eligibility",
  "intent": {
    "claim": "Participation guarantee is EUR 6,000 (2% of the EUR 300,000 TED value)",
    "citation": {
      "notice": "769674-2026",
      "locator": "§2.2.2.1, PDF p27 / printed 20",
      "url": "https://ted.europa.eu/en/notice/-/detail/769674-2026"
    }
  },
  "tool_call": {
    "name": "extract_criteria",
    "arguments": { "notice_id": "769674-2026", "rule": "participation_guarantee" }
  },
  "tool_response": {
    "ok": true,
    "value": { "participation_guarantee_eur": 6000, "basis": "TED procedure-level value EUR 300,000" }
  },
  "independent_check": {
    "checker": "verifier-core",
    "method": "reread_tender_pdf_page",
    "source": "RFP PDF p27 §2.2.2.1 (printed page 20)",
    "observed": {
      "participation_guarantee_eur": 4000,
      "basis": "2% of EUR 200,000 excl. VAT and option"
    },
    "mismatch": true
  },
  "status": "FAILED",
  "reason": "A naive extractor trusted TED's headline value (EUR 300,000). The notice sets the guarantee on the initial budget excl. option (EUR 200,000), so EUR 4,000. No 'done'."
}
```

Do not implement a hidden demo switch that writes a fake number. Implement a naive extractor path that uses the TED procedure-level value (€300,000) for the guarantee, and a verifier path that re-reads §2.2.2.1 and uses €200,000.
