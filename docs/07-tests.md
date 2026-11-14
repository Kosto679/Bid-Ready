# Tests

Use pytest. Put tests under `tests/`. Run `pytest -q` after the Sat 21:00 block, before any large Sunday change, before rehearsal (Sun 14:30), and before recording (Sun 16:00).

## Golden end-to-end: `tests/test_golden_ktp.py`

Run the ΚτΠ path offline against `data/tender-demo/769674-2026/` (do not require a live TED call for this test).

Use a fixture profile of an 8-person Athens software studio that:

- has a 3-year turnover you choose and document (if under €400,000 total, turnover must be `missing`; if at or above, `meets` the turnover sum rule, still not the experience or ISO rules)
- does not hold all six ISOs
- answers the public-sector projects question with none, or with projects that are not escrow-payment systems

Assert:

1. `check_eligibility("769674-2026", profile)` returns `verdict == "not_eligible"`.
2. The checklist includes a `missing` (not `unclear`) experience rule citing §2.2.6.1 with `pdf_page` / `printed_page`.
3. The checklist includes a `missing` ISO rule citing §2.2.7.
4. A participation-guarantee claim is produced by the naive TED-headline path as **€6,000**.
5. `verify(...)` writes a receipt for that claim with `status == "FAILED"`, `independent_check.observed` participation guarantee **€4,000**, and a source that points at the tender page or extract for §2.2.2.1 (PDF p27 / printed 20) — not only at `requirements.json`.
6. The pack is **not** marked `ready`.
7. `draft_cover_letter` produces a Greek-language file that exists on disk.
8. `build_pack` produces a ZIP that contains ASCII-only entry names and includes the letter, a checklist, `receipts.json`, and `deadline.ics`.
9. The `.ics` represents Monday 7 Dec 2026, 14:00 Europe/Athens (`TZID=Europe/Athens` or `20261207T120000Z`).

If onboarding is not wired in this test, pass the profile as JSON. The test must still call the same functions the MCP tools use.

## Small tests

### `tests/test_page_offset.py`

For the ΚτΠ RFP PDF, printed page = PDF page minus 7.

Assert at least:

- §2.2.5 turnover is PDF page 33 and printed page 26
- §2.2.2.1 participation guarantee is PDF page 27 and printed page 20

If citations are loaded from `requirements.json`, assert those two mappings match the files, and that a helper `printed_page(pdf_page) == pdf_page - 7` holds for body pages.

### `tests/test_ics_timezone.py`

Build the deadline file for this tender. Assert it is not a floating time (no date-time without `Z` or `TZID`). Accept either:

- `DTSTART;TZID=Europe/Athens:20261207T140000`, or
- `DTSTART:20261207T120000Z`

### `tests/test_zip_ascii.py`

Open a pack ZIP (or a fixture ZIP built by `build_pack`). Assert every entry name is ASCII (`name.encode("ascii")` succeeds). Reject Greek letters in entry names.

### `tests/test_guarantee_calc.py`

- 2% of 200_000 == 4_000 (correct participation guarantee; basis is initial budget excl. VAT and option).
- 2% of 300_000 == 6_000 (naive TED-headline figure).
- 4% of 200_000 == 8_000 (performance guarantee at signature).
- The verifier, given a claim of 6_000 and an observed page value of 4_000, returns `FAILED`.

## Running

```bash
pytest -q
pytest -q tests/test_golden_ktp.py
```

A live TED test, if you add one, must be marked so it can be skipped offline (`pytest -m "not network"` or similar). The golden test must pass with no network.
