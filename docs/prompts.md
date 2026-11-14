# Ready-to-paste prompts

Use these in Cursor or Claude Code, in order. Paste one block, wait until the "Done when" in `docs/06-build-plan.md` is met, run any tests, then `git commit`. Read `AGENTS.md` first. Do not invent tender facts; use `docs/05-test-case-ktp.md` and `data/tender-demo/`.

---

## 1. Sat 15:00–16:00 — Scaffold, key, receipts, find_tenders

```
Read AGENTS.md and docs/03-receipts-and-verifier.md.

Set up this Python 3.11+ project:
- requirements.txt with fastapi, uvicorn, pytest, mcp, python-docx, httpx or requests, icalendar or a small .ics writer, python-dotenv
- .gitignore including .env, .venv, receipts.db, __pycache__, .pytest_cache
- .env.example with LLM_API_KEY= and LLM_API_BASE= placeholders (no real secrets). I will copy it to .env myself.
- app/ package with FastAPI in app/main.py and a /health endpoint

Implement app/receipts.py first: the SQLite schema and write_receipt() from docs/03-receipts-and-verifier.md. Every later tool must call write_receipt before returning. Same idempotency_key returns the first row and must not insert a second time.

Then implement app/ted.py and a FastAPI route plus a CLI entry that POSTs to https://api.ted.europa.eu/v3/notices/search (no API key) with:
place-of-performance = EL* AND classification-cpv = 72* AND form-type = competition AND deadline-receipt-tender-date-lot >= 20261116
Fields: publication-number, notice-title, buyer-name, classification-cpv, deadline-receipt-tender-date-lot, deadline-receipt-tender-time-lot, place-of-performance, buyer-country, form-type, notice-type, publication-date. onlyLatestVersions true, limit 50. Timeout ~90s.

Also support loading one notice by publication number, including 769674-2026. Print title, buyer, deadline, CPV, and https://ted.europa.eu/en/notice/-/detail/{publication-number}.

If TED times out, fall back to data/tender-demo/769674-2026/ (unzip tender-demo.zip there if needed) and write an UNVERIFIED receipt for the live hop.

Write a receipt for the search call. Show me how to run it. Do not build scoring, eligibility, UI, or extras yet.
```

---

## 2. Sat 16:00–18:00 — Onboarding + score_tenders

```
Read AGENTS.md, docs/04-scoring.md, and docs/02-architecture.md (CompanyProfile).

Add onboarding: accept two typed lines (or a JSON profile) and produce a CompanyProfile. Ask only for missing facts: turnover as a 2023+2024+2025 total in EUR, certificates, and public-sector projects in the last 5 years. If the projects question is skipped, store public_sector_projects_last_5y as null (eligibility will later mark experience UNCLEAR, not missing). Infer size, location, and likely CPV codes when possible. The runtime LLM key is in .env (not Cursor's key); if the key is missing, accept a fully typed JSON profile.

Implement score_tenders exactly as docs/04-scoring.md: fit_score = round(100 * (0.25*cpv + 0.25*value_fit + 0.25*place + 0.25*deadline)). TED metadata plus the profile only. Do not read requirements.json. Each result has a one-sentence reason built from those four fields.

Use a demo profile: an 8-person Athens software studio. Run find_tenders + score_tenders and print a ranked shortlist. TED 769674-2026 should appear with an honest, probably low, score — do not boost it because it is the demo tender.

Every tool writes a receipt. Commit when the shortlist looks right. No eligibility, letter, or UI yet.
```

---

## 3. Sat 18:00–20:00 — check_eligibility

```
Read AGENTS.md, docs/05-test-case-ktp.md, and docs/02-architecture.md (check_eligibility).

Implement check_eligibility for notice 769674-2026. Use data/tender-demo/769674-2026/requirements.json as a clause index only (what to check, section, pdf_page, doc_page). Confirm values against data/tender-demo/769674-2026/text/ (rfp_compact.txt has ---PDF pN--- markers; pages.json is per-page). Printed page = PDF page minus 7.

Return meets / missing / unclear for at least: turnover (§2.2.5, PDF p33 / printed 26), experience (§2.2.6.1, p33–34), ISOs (§2.2.7, p36–37), participation guarantee (§2.2.2.1, PDF p27 / printed 20). Drop team-CV rules if needed. Experience is missing only if the profile answered the public-sector projects question; otherwise unclear.

For the 8-person Athens demo profile (answer projects as none, or two small sites that are not escrow), verdict must be not_eligible, citing §2.2.6.1 and typically §2.2.7, plus a one-line partnership note. Do not fake eligible.

Also emit a naive participation-guarantee claim of EUR 6,000 computed as 2% of the TED headline value EUR 300,000. The correct figure is EUR 4,000 (2% of EUR 200,000). Verification comes in the next block.

Write receipts. Do not implement the full verifier, letter, pack, or UI yet.
```

---

## 4. Sat 21:00–23:00 — Letter + verifier + guarantee FAIL

```
Read AGENTS.md, docs/03-receipts-and-verifier.md, and docs/05-test-case-ktp.md.

Implement draft_cover_letter: a Greek-language letter framed as outreach to a possible consortium partner because the firm is not eligible alone. Markdown is fine. ASCII file name, e.g. consortium_letter_el.md.

Implement verify: for each claim, re-open the cited page in data/tender-demo/769674-2026/text/ (or the PDF). Do not grade by re-reading requirements.json alone. Statuses: VERIFIED, UNVERIFIED, FAILED. UNVERIFIED and FAILED are not "ready".

Wire a naive extractor path that trusts TED's procedure-level value EUR 300,000 and claims a EUR 6,000 participation guarantee. The verifier must re-read §2.2.2.1 (PDF p27 / printed 20), observe EUR 4,000, and write status FAILED. Do not add a hidden demo switch. Do not plant a EUR 300,000 vs EUR 400,000 turnover error.

The pack/run must not be marked ready when that receipt is FAILED.

Start tests/test_golden_ktp.py and tests/test_guarantee_calc.py as specified in docs/07-tests.md. Sketch is enough if time is short; the assertions should already fail or pass honestly.

Every tool writes a receipt. Show me the FAILED receipt JSON and the letter path.
```

---

## 5. Sat 23:00–00:30 — build_pack

```
Read AGENTS.md, docs/02-architecture.md (build_pack), and docs/07-tests.md.

Implement build_pack for the current run. Create a ZIP with ASCII entry names only (no Greek characters in names):
- consortium_letter_el.md (or .docx)
- eligibility_checklist.md
- receipts.json
- deadline.ics

deadline.ics must be Mon 7 Dec 2026, 14:00 Europe/Athens, with TZID=Europe/Athens or as 20261207T120000Z. No floating local times.

Do not mark the pack ready if any required receipt is FAILED or UNVERIFIED. Include the FAILED guarantee receipt in receipts.json.

Add tests/test_ics_timezone.py and tests/test_zip_ascii.py, and extend the golden test to open the ZIP and the .ics.

If you have energy, stub the six FastMCP tool signatures in app/mcp_server.py (stdio) pointing at the real functions. If not, leave MCP for Sunday.

Show me the ZIP path and confirm entry names are ASCII.
```

---

## 6. Sun 08:00–11:00 — Curated UI

```
Read AGENTS.md, docs/02-architecture.md (Web UI flow), and docs/08-demo-and-submission.md.

Build a simple one-page or short-wizard web UI on FastAPI that walks:
1) Onboard (two typed lines; ask turnover, certificates, public-sector projects last 5 years)
2) Ranked matches with fit score and one-line reason (do not auto-select the ΚτΠ tender as best fit)
3) Prepare bid — eligibility + Greek consortium letter + verify
4) Receipts list; refuse to show "ready" until verify has finished; the FAILED EUR 6,000 vs EUR 4,000 guarantee receipt must be visible
5) Download the ZIP

Reuse the existing Python functions. Do not rewrite Saturday's scoring, eligibility, or verifier unless a test is failing. Run pytest first; if you need to change those modules, keep the golden test passing.

The 3-minute path must work without a terminal. Commit when it does.
```

---

## 7. Sun 11:00–13:00 — MCP, README, tests polish

```
Read AGENTS.md, docs/02-architecture.md (MCP tools), docs/07-tests.md, and docs/08-demo-and-submission.md (README checklist).

Wire all six tools in a FastMCP stdio server (app/mcp_server.py): find_tenders, score_tenders, check_eligibility, draft_cover_letter, verify, build_pack. Each returns real results plus receipts. Document the Cursor MCP command (python -m app.mcp_server or equivalent).

Finish the golden end-to-end test and the small tests (page offset, ics timezone, ascii zip names, guarantee calc). pytest -q must pass offline.

Draft README.md and a short project-details blurb for submission, following the checklist in docs/08-demo-and-submission.md. No secrets. State that requirements.json is a human-curated fixture and that the verifier re-reads the tender text/PDF.

Do not start extras. After this I will record an insurance video of the Cursor MCP path myself.
```

---

## 8. Sun 13:00–14:30 — Extras only if core is solid

Only paste this if the UI or scripted path already works and the golden test passes. Otherwise paste: "Do not add extras. Fix failing tests and demo-blocking bugs in the core loop only. See docs/01-scope.md never-cut list."

```
The core loop works. Add at most one extra, in this order, and stop if it risks the demo. Read docs/01-scope.md extras list.

Preferred order:
1) Live model extraction of a ΚτΠ page that may misread the guarantee or budget, still caught by verify (keep the naive TED-headline path as backup).
2) A fuller MCP walkthrough prompt in the README: "Find a Greek IT tender my company can bid on and prepare the pack."
3) A live receipt wall in the UI (green/amber/red, no "ready" until checks finish).
4) Firecrawl website-paste onboarding (sponsor tool). Still ask for turnover, certificates, and public-sector projects if missing from the site. Store any Firecrawl key in .env, not the repo.
5) Partial live extraction of a few fields from data/tender-demo/backup-OLPA-26PROC020181047/ through verify. Do not build a new requirements.json.
6) Pre-fill the buyer ΕΕΕΣ PDF fields we can (Parts II, III, IV only section α, VI). A human still signs. Do not try to scrape ΕΣΗΔΗΣ for the .xml.
7) MITOS tax clearance: GET https://api.digigov.grnet.gr/v1/services-extended/439993 (no key) and show official steps on a missing tax-clearance line.
8) A "check again" TED button. Drop this first.

Keep pytest passing. Commit. No refactors of Saturday's core unless a test fails.
```

---

## 9. Sun 14:30–16:30 — Freeze features, tests, demo readiness

```
No new features. Run pytest -q (golden test and small tests). Fix only failures or bugs that would break the 3-minute demo in docs/08-demo-and-submission.md, including the 15-second MCP (or terminal) check_eligibility call that returns the FAILED guarantee receipt.

Confirm the offline path works from data/tender-demo/769674-2026/ with TED disabled. Confirm the ZIP has ASCII names and the .ics shows 14:00 Athens.

Do not touch extras. After tests pass, stop so I can rehearse and record the video.
```
