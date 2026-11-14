# Demo and submission

Rehearse until the live walkthrough fits under three minutes. The MCP call is part of the main script, not an optional close. Other extras are only for the last 10 seconds, and only if they already work.

Times below are the spoken script, not the build plan. All clock times in the build plan are Europe/Athens.

## Why it matters (opening statistic)

Use this checked figure only: a 2024 Powergame report on Greek startups found 67.9% have never bid on a public contract, and 55% wanted help preparing the dossier.

Source: https://www.powergame.gr/start-ups-digital/1039587/i-athanati-grafeiokratia-krata-tis-ellinikes-startups-makria-apo-ta-erga-tou-dimosiou/

## 3-minute script

### 0:00–0:10 — Why it matters

Open with the statistic above. Then one line: "That paperwork is the job. We finish a checked pack, and we do not mark it ready on the agent's word."

### 0:10–0:25 — Onboard

Paste two lines (or a website) about an 8-person Athens studio. Show the profile appear, and the agent asking for turnover, certificates, and public-sector projects in the last 5 years. Answer that last question (e.g. "none" or "two small sites, not escrow") so experience can be missing rather than unclear.

### 0:25–0:55 — Ranked matches, then a deliberate choice

Show two or three tenders already scored and sorted, each with a one-line reason from the TED formula (CPV, value vs turnover, place, days to deadline). The app searches TED in the profile's CPV divisions and scores every open notice (49 for IT on Sat 14 Nov), then shows the best 8. ΚτΠ scores **77 and ranks about 4th** for the demo studio: one clean CPV match, Greece, 23 days to prepare. Point at it on the list and click "Prepare bid" to open the fit report. Say: "A strong fit on paper: right CPV, right place, three weeks to prepare. But a fit score isn't eligibility. Let's check." Open the real TED URL if the network is up: https://ted.europa.eu/en/notice/-/detail/769674-2026

*(Updated Sat 14 Nov: the ranking moves as tenders open and close. Re-check it on the morning of the demo. If ΚτΠ drops out of the top 8 it still appears, marked "Demo tender, not in your top 8".)*

### 0:55–1:35 — Prepare bid

Eligibility comes back as not eligible, with citations: missing escrow-payment projects (§2.2.6.1), missing ISOs (§2.2.7), turnover if the demo profile is under €400,000 total. One sentence on what a partnership would need. Open the Greek letter as outreach to a possible consortium partner. The judge should see a document, not only a chat bubble.

### 1:35–2:05 — The receipt

The participation guarantee was computed as €6,000 because a naive extractor trusted TED's €300,000 headline; the cited PDF page says €4,000 (2% of €200,000). The receipt is FAILED. Say: "This is the exact mistake that headline invites. We do not mark this ready. That is the product."

### 2:05–2:30 — Handover

Unzip the pack live (ASCII names): consortium letter, checklist, receipts, `.ics` with the 7 Dec 14:00 Athens deadline. "A human signs and submits on ΕΣΗΔΗΣ. We stop here."

### 2:30–2:50 — Agents can call it (~15 seconds)

In Cursor, with the MCP server attached, one prompt: check eligibility on this tender. Show the tool result including the FAILED guarantee receipt. "People get a pack. Other agents get a receipt, not a vibe." If MCP is flaky, show the same call in a terminal. Do not skip this beat.

### 2:50–3:00 — Close, then optional wow

Stop and offer questions. If an extra is working, use this last slice: the receipt wall, Firecrawl onboarding, or "you're missing tax clearance — here is the official MITOS procedure."

Ready now: the **Model check** panel. "We ran Gemini on the contest's Google Cloud over nine facts from this tender. Given the PDF page, it got 27 of 27 right. Given only the TED headline, it called €300,000 the budget every time, the same trap, and the verifier failed it."

## Video plan

- **~Sunday 11:00:** record a rough insurance take of the scripted Cursor path, in case the UI is not ready at 16:00.
- **Sunday 16:00–16:30:** run the golden test, then record the official demo video (required for submission). Narrate the rehearsed script over the screen recording. The video must work fully offline against the local pack. The guarantee FAILED receipt must not depend on TED being up.
- Keep the official file ready to play at the Sunday 19:00 live presentation if the live run fails. If the official take fails, recut; do not rebuild. Fall back to the 11:00 insurance take if needed.

## README and project details (draft Sunday 11:00–13:00)

Do not leave this until 17:30. Include:

- One-paragraph what it is (guided bid pack + receipts; nothing marked ready until a second checker re-reads the tender)
- The problem (use the Powergame statistic and a link)
- How to run: `.env` setup (no secrets in the repo), `pytest`, UI, MCP stdio command
- Demo profile and how to replay TED 769674-2026 offline
- Honest note: `requirements.json` is a human-curated fixture / clause index; the verifier re-reads the PDF or extracted text
- What is out of scope (no ΕΣΗΔΗΣ submission)
- Commit history / "built after Saturday 13:00; fixtures prepared beforehand"

## Judge Q&A (short answers)

**Why isn't this ChatGPT on TED?** The user never has to know a CPV code. Every rule cites a clause. A separate verifier re-reads the tender page. The agent's own "success" is not accepted. The judge can open the ZIP.

**Did you hand-annotate this? Does it work on a tender you didn't prepare?** Yes: `requirements.json` is human-curated ground truth for this one notice, prepared as a fixture so we could demo a real, messy tender this weekend. The verifier does not stop at that file: it re-opens the cited PDF or text page. Automatic extraction is the next step. (A live pass on the ΟΛΠΑ backup exists in the code but is parked, not shown in the app.) We also asked the organizers whether pre-start fixtures are allowed.

**Is this pre-built?** Before the official Saturday 13:00 start we mapped a real tender, cached documents, and confirmed the TED API. Search, scoring, eligibility, the letter, the verifier, the pack, and the UI were built after that start. Happy to show commit times.

**What do people want? What do agents want?** A small firm gets a ranked shortlist, a straight eligibility answer, a consortium letter, and a ZIP. In the demo, Cursor calls `check_eligibility` over MCP and gets a FAILED receipt, not a vibe.

**You said they're not eligible. Is that a demo of failure?** No — it is the product being honest. This tender needs five escrow-payment projects and six ISOs. Telling a small firm they qualify would be the lie. We show why, cite the clause, and still hand over a checked pack and a letter they can send to a partner.

**Why a cover letter? ΕΣΗΔΗΣ doesn't ask for one.** Agreed: the documents that usually go on ΕΣΗΔΗΣ are the ΕΕΕΣ and the offers. Given the "not eligible alone" verdict, the Greek letter is the next useful step — a draft to a possible partner. Filling the ΕΕΕΣ is an extra if time allows.

**Did you plant the guarantee error?** It is a known trap, and we used it on purpose. TED really shows €300,000. A naive extractor that trusts that headline computes 2% as €6,000. The notice sets the guarantee on €200,000, so €4,000. We did not hide a random switch; we used the exact mistake that figure invites, and the verifier catches it against the PDF page. It isn't hypothetical: in our eval, Gemini given only the TED metadata reported €300,000 as the initial budget in 3 of 3 trials.

**Isn't the verifier just observability?** It blocks "ready". Logs would still let the agent claim success. We refuse to mark the pack ready without independent checks on the tender pages, read writes back, and use idempotency keys so a retry cannot double-write.

**What if TED is down right now?** The ΚτΠ documents are in `data/tender-demo/` from `tender-demo.zip`. A downed live source is UNVERIFIED, not success. The guarantee catch and the ZIP work offline.
