# Scope

Do not start extras until the core loop works end to end. The reusable verifier is the engine; Bid-Ready is the only specialist to demo.

## Core (must ship)

Build one curated path, exposed as six MCP tools and a simple web UI.

1. **Onboard in 30 seconds.** Accept a website paste or two typed lines. Build a company profile (what they do, size, location, likely CPV codes). Ask only for what you could not work out: turnover (2023+2024+2025 total), certificates, and public-sector projects in the last 5 years. If the projects question is skipped, experience must be `UNCLEAR`, not `missing`.
2. **Ranked matches.** `find_tenders` calls TED. `score_tenders` ranks with the formula in `docs/04-scoring.md` (TED metadata only). Each match gets a fit score and a one-line plain-language reason built from those fields. The ΚτΠ demo tender should score honestly, probably low.
3. **Prepare bid — eligibility.** `check_eligibility` compares the profile to the notice. Every rule is `meets`, `missing`, or `unclear`, with a citation (section + PDF page + printed page). For a typical small firm on TED 769674-2026, if they answered the projects question, the honest verdict is **not eligible**, plus a short note on what a partnership would need.
4. **Cover letter (stays in core).** `draft_cover_letter` writes the letter in Greek. ΕΣΗΔΗΣ bids may not require a cover letter (the documents that usually matter are the ΕΕΕΣ and the technical and financial offers). Frame the draft as outreach to a possible consortium partner: you cannot bid alone; here is who you are and what you would bring.
5. **Independent verify.** `verify` re-opens the cited tender text or PDF page (not only `requirements.json`), compares each claim, and writes receipts (`VERIFIED` / `UNVERIFIED` / `FAILED`). Nothing is marked ready until checks have run. A naive extractor that trusts TED's €300,000 headline will compute a €6,000 participation guarantee; the notice says €4,000. That must come out `FAILED`.
6. **Handover ZIP, then stop.** `build_pack` zips the letter, the eligibility checklist, the receipts, and a deadline `.ics` for Mon 7 Dec 2026, 14:00 Europe/Athens (`TZID=Europe/Athens` or `12:00Z`). Use ASCII file names inside the ZIP. Do not submit on ΕΣΗΔΗΣ. A human signs.

## Never cut

Even if behind, ship all of the following:

- A company profile in, including the public-sector projects question
- Scored matches from the TED formula
- An eligibility list with citations on TED 769674-2026
- A Greek consortium letter
- A verifier that `FAILED`s the €6,000 vs €4,000 guarantee against the actual PDF page
- A ZIP with a timezone-correct `.ics`
- One walkthrough: the web UI, or a clean scripted path in Cursor, including a ~15-second MCP (or terminal) call to `check_eligibility` that returns the `FAILED` receipt

Cut extras first, then polish.

## Extras (only if the core works)

Sunday 13:00–14:30 Europe/Athens is the slot. Do them in this order. Stop at the first one that would put the demo at risk. The short MCP eligibility call is already in the main demo; the fuller agent-to-agent walkthrough remains an extra.

1. **Live catch of a real model error.** Let the model read a ΚτΠ notice page and get budget, guarantee, or turnover wrong on its own. Keep the naive TED-headline guarantee miss as backup if the model is accurate.
2. **Fuller agent-to-agent walkthrough.** In Cursor or Claude Code: "Find a Greek IT tender my company can bid on and prepare the pack." The other agent calls several tools, hits the `FAILED` receipt, and only then continues.
3. **Live receipt wall.** Claims turn green / amber / red with a link to the clause. The screen refuses to show "ready" until checks have finished. A static receipt list is enough if this slips.
4. **Firecrawl website-paste onboarding** (sponsor tool, about 30 minutes). Still ask for turnover, certificates, and public-sector projects if they are not on the site. Do this before forms or watch mode. Two typed lines remain the core path.
5. **Partial live extraction on the ΟΛΠΑ backup** (ΑΔΑΜ 26PROC020181047). Extract a few rules (value, deadline, one ISO or turnover line) live from the PDF and run them through the verifier. Even two or three fields are enough. Do not rebuild `requirements.json` for ΟΛΠΑ.
6. **Fill the ΕΕΕΣ / ESPD and key declarations.** Pre-fill the buyer's ΕΕΕΣ (Parts II, III, IV only section α, VI) and draft the Russia-sanctions declaration. A human still signs. The official ESPD `.xml` sits only on ΕΣΗΔΗΣ (JS-only, system 589064) and is not in the public ZIP — work from the PDF. One form done well beats five stubs.
7. **What's missing + MITOS.** On a missing tax-clearance line, GET `https://api.digigov.grnet.gr/v1/services-extended/439993` (no key) and show the official steps, cost, and gov.gr link. One procedure is enough.
8. **Watch mode.** A "check again" button that re-runs the TED query for the same profile. Drop this first.

## Out of scope this weekend

- Submitting on ΕΣΗΔΗΣ
- Fetching the ESPD `.xml` from the JS-only ΕΣΗΔΗΣ page
- Parsing the 137-page διακήρυξη from scratch when `requirements.json` plus `text/` exist
- A second product or domain
