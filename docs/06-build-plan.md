# Build plan

All times are Europe/Athens (EET, UTC+2). Code freeze is Sunday 15 Nov 2026, 18:00. This plan is sized for one person plus a coding agent, from Saturday about 15:00 to that freeze.

## Habits (every block)

- After each "Done when", make a git commit so you can roll back if later work breaks the loop.
- Do not start extras until the core path works.
- Run tests after you have them (from the Sat 21:00 block onward). Run the golden test before Sunday rehearsal and before recording.
- Do not skip dinner or sleep to add extras.

## Blocks

### Sat 15:00–16:00 — Scaffold, key, receipts, find_tenders

**Tasks**

- Put a runtime LLM API key in `.env` (product backend, not Cursor). Add `.env` to `.gitignore`. Add `.env.example` without the secret.
- Scaffold Python 3.11+, FastAPI, pytest, `requirements.txt`.
- Unzip `tender-demo.zip` into `./data/tender-demo/`.
- Create the SQLite receipts table and `write_receipt()` (`docs/03-receipts-and-verifier.md`). Every tool from here on writes a receipt.
- Implement `find_tenders` against POST `https://api.ted.europa.eu/v3/notices/search`. Load TED 769674-2026 by number.

**Done when:** The key is set and not in git. You can list real Greek IT tenders, TED 769674-2026 is loadable, and a tool call leaves a receipt row. Commit.

**If behind:** Fall back to the unzipped local pack and still print the ΚτΠ notice. Do not skip receipts or the `.env` setup.

### Sat 16:00–18:00 — Onboarding + score_tenders

**Tasks**

- Build a company profile from two typed lines. Ask for turnover, certificates, and public-sector projects in the last 5 years.
- Implement `score_tenders` with the formula in `docs/04-scoring.md`. One-line reasons from those four fields only.

**Done when:** A demo small-firm profile gets a ranked shortlist. The ΚτΠ tender has an honest, probably low, score and a reason you can read aloud. Commit.

**If behind:** Skip website paste (Firecrawl is an extra). Type the profile as JSON. Do not score against `requirements.json`.

### Sat 18:00–20:00 — check_eligibility

**Tasks**

- Implement `check_eligibility` for 769674-2026. Use `requirements.json` as the clause index. Confirm each citation against `text/` or the PDF page.
- Statuses: meets / missing / unclear, each with section, PDF page, and printed page.
- Experience is `missing` only if the projects question was answered; otherwise `unclear`.
- Cover turnover, experience, ISO, and participation guarantee. Drop team-CV detail if needed.

**Done when:** The small-firm profile is honestly `not_eligible`, citing §2.2.6.1 and §2.2.7, plus a one-line partnership note. Commit.

**If behind:** Those four rules only.

### Sat 20:00–21:00 — Dinner

**Done when:** You ate.

**If behind:** Do not skip dinner to start extras.

### Sat 21:00–23:00 — Letter + verifier + guarantee FAIL

**Tasks**

- `draft_cover_letter` in Greek, framed as consortium-partner outreach. Markdown is fine.
- Wire `verify` to re-read the cited PDF or `text/` page, not only `requirements.json`.
- Naive extractor trusts TED's €300,000 value so the guarantee comes out €6,000 and `FAILED` against §2.2.2.1 (€4,000). Do not invent a turnover plant.
- Start the golden pytest (`docs/07-tests.md`).

**Done when:** The letter opens. The guarantee receipt is `FAILED` and the pack is not marked ready. The test is at least sketched. Commit.

**If behind:** Markdown letter is enough. A fully live model catch is an extra.

### Sat 23:00–00:30 — build_pack

**Tasks**

- ZIP with ASCII file names: letter, checklist, `receipts.json`, `deadline.ics`.
- `.ics` for Mon 7 Dec 2026, 14:00, `TZID=Europe/Athens` or `12:00Z`. Open it in Outlook or Google Calendar and check the time.
- Stub the six MCP signatures if you have energy.
- Finish the golden test if you can.

**Done when:** The ZIP opens on Windows and the `.ics` shows 14:00 Athens. Commit.

**If behind:** Skip MCP until Sunday morning. Do not ship Greek characters in ZIP entry names.

### Sun 00:30–08:00 — Sleep

**Done when:** You are rested.

**If behind:** Do not skip sleep to add extras.

### Sun 08:00–11:00 — Curated UI

**Tasks**

- One-page (or short wizard) UI: onboard → ranked matches → Prepare bid (eligibility + letter) → receipts → download ZIP.
- Refuse to show "ready" until verify has finished.

**Done when:** The 3-minute path works without touching a terminal. Commit.

**If behind:** Ship a clean Cursor walkthrough of the same six tools and still record that.

### Sun 11:00–13:00 — MCP, README, insurance video

**Tasks**

- Wire the six MCP tools to the real functions (FastMCP, stdio).
- Draft README and the submission project details.
- Around 11:00, record a rough insurance video of the scripted Cursor path.
- Polish the "not eligible" wording. Fix citation bugs.

**Done when:** Cursor can call `check_eligibility` and get the `FAILED` receipt. README and project details exist in draft. Insurance video is on disk. Commit.

**If behind:** Keep the insurance video of the scripted path. Do not leave README until 17:30.

### Sun 13:00–14:30 — Extras or fix core

**Tasks**

- Only if the core path is solid, do extras in the order in `docs/01-scope.md`.
- If the core is shaky, use this block to fix it.

**Done when:** Either one extra works, or the core is tighter. Not both at the cost of the demo.

**If behind:** Skip all extras.

### Sun 14:30–16:00 — Rehearse

**Tasks**

- Run the golden test first.
- Rehearse the 3-minute script twice, including the 15-second MCP beat (`docs/08-demo-and-submission.md`).
- Fix only bugs that would break the demo or the video.

**Done when:** Golden test passes. Timing fits. ZIP, receipts, and the not-eligible story work offline.

**If behind:** Drop live TED; use the local pack. If MCP is flaky, use a terminal call for that beat.

### Sun 16:00–16:30 — Record official video

**Tasks**

- Run the golden test again.
- Record the official demo video. Narrate the rehearsed script over the screen recording.
- Keep this file as the Sunday 19:00 backup.

**Done when:** You have a file you would submit even if Wi-Fi dies at 17:00, and would play for judges at 19:00 if the live run fails.

**If behind:** No new features. If a take fails, recut, do not rebuild. The 11:00 insurance take is the fallback.

### Sun 16:30–18:00 — Submit

**Tasks**

- Submit the repo, the demo video, and project details. Buffer. No new features after 16:30.

**Done when:** Submitted before 18:00. Laptop and recorded video ready for a possible 19:00 presentation.

**If behind:** Code freeze is 18:00 sharp.

## After 18:00

Shortlist 18:00–19:00. Semifinalists present at 19:00 — use the same three-minute script; if the live run fails, play the recorded video. Finalists announced at 20:00. Monday 18:00–18:30 SNFCC pitch is only if you make that cut.
