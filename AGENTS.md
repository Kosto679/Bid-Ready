# Bid-Ready — agent instructions

Read this file first. Follow it for every change. Details live under `docs/`. Do not invent tender facts; use `docs/05-test-case-ktp.md` and `data/tender-demo/`.

## One-liner

Bid-Ready is a guided path from a short company profile to a checked bid pack for EU/Greek public tenders. Nothing is marked ready until an independent verifier re-reads the tender itself and issues a receipt.

## Stack

- Python 3.11+
- FastAPI
- MCP Python SDK (FastMCP), stdio
- SQLite for receipts
- python-docx or Markdown for the letter
- A simple one-page web UI
- Runtime LLM API key for the **product backend** (onboarding, one-line reasons, Greek letter): store it in `.env`, add `.env` to `.gitignore`. This is not the Cursor/Claude Code key.
- TED Search API (`https://api.ted.europa.eu/v3/notices/search`, POST, no key)
- Local tender pack at `./data/tender-demo/` (unzip `tender-demo.zip` there)

## Golden rules

1. Build receipts first. Every tool must call `write_receipt()` before it returns.
2. Never mark a pack or run `ready` / `done` until `verify` has finished. `UNVERIFIED` is not done.
3. The verifier re-reads the cited tender PDF or extracted text page. It must not treat `requirements.json` as the only source of truth.
4. Commit after every "Done when" checkpoint in `docs/06-build-plan.md`. Do not rewrite working Saturday code without a passing golden test.
5. Run the golden end-to-end test (`docs/07-tests.md`) before big changes, before Sunday rehearsal, and before recording.
6. Use ASCII file names inside the handover ZIP (no Greek characters in entry names).
7. Write the deadline `.ics` with `TZID=Europe/Athens`, or as `12:00Z` for 14:00 Athens. Never use a floating local time.
8. For the ΚτΠ RFP PDF, printed page = PDF page minus 7. Store both `pdf_page` and `printed_page` on every citation.
9. `score_tenders` uses TED metadata plus the profile (see `docs/04-scoring.md`). The one exception: once a tender's turnover rule has been read from its own text and VERIFIED, the value factor uses that rule (`app/rule_cache.py`). Never score against `requirements.json` directly.
10. Do not start extras until the core loop in `docs/01-scope.md` works end to end.
11. Do not submit a bid on ΕΣΗΔΗΣ. Stop at the handover ZIP. A human signs.

## Repo layout

```
.
├── AGENTS.md
├── README.md
├── .env                 # git-ignored; runtime LLM key
├── .env.example
├── .gitignore
├── requirements.txt
├── app/
│   ├── main.py          # FastAPI
│   ├── receipts.py      # SQLite schema + write_receipt()
│   ├── ted.py           # find_tenders
│   ├── scoring.py       # score_tenders
│   ├── profile.py       # onboarding
│   ├── eligibility.py   # check_eligibility
│   ├── letter.py        # draft_cover_letter
│   ├── verifier.py      # re-read PDF/text pages
│   ├── pack.py          # build_pack
│   └── mcp_server.py    # FastMCP, six tools
├── web/                 # simple curated UI
├── tests/
│   ├── test_golden_ktp.py
│   ├── test_page_offset.py
│   ├── test_ics_timezone.py
│   ├── test_zip_ascii.py
│   └── test_guarantee_calc.py
├── data/
│   └── tender-demo/     # unzip tender-demo.zip here
│       ├── 769674-2026/ # README, requirements.json, docs/, text/
│       └── backup-OLPA-26PROC020181047/
└── docs/                # this instruction pack
```

## Commands

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
# copy .env.example to .env and set the runtime LLM key
# unzip tender-demo.zip into ./data/tender-demo/

pytest -q
uvicorn app.main:app --reload --port 8000
# MCP (stdio): python -m app.mcp_server
```

TED search (no key): POST `https://api.ted.europa.eu/v3/notices/search` with `Content-Type: application/json`. Use `form-type = competition`, `place-of-performance = EL*`, `classification-cpv = 72*`, `deadline-receipt-tender-date-lot >= 20261116`. Set `checkQuerySyntax` true only to validate; that mode does not search. See `docs/05-test-case-ktp.md` and the TED API docs: https://docs.ted.europa.eu/api/latest/search.html

## Doc index

- [docs/01-scope.md](docs/01-scope.md) — must-ship vs extras; never-cut list
- [docs/02-architecture.md](docs/02-architecture.md) — components, data flow, MCP tool signatures, UI flow
- [docs/03-receipts-and-verifier.md](docs/03-receipts-and-verifier.md) — SQLite, write_receipt(), statuses, how verify works
- [docs/04-scoring.md](docs/04-scoring.md) — visible TED-metadata fit formula
- [docs/05-test-case-ktp.md](docs/05-test-case-ktp.md) — TED 769674-2026 facts, traps, expected verdict
- [docs/06-build-plan.md](docs/06-build-plan.md) — hour-by-hour plan and checkpoints
- [docs/07-tests.md](docs/07-tests.md) — golden pytest and small tests
- [docs/08-demo-and-submission.md](docs/08-demo-and-submission.md) — demo script, video, README, judge Q&A
- [docs/prompts.md](docs/prompts.md) — ready-to-paste prompts, one per build block
