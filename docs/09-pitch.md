# Pitch (demo day)

The pitch drives the app. Any screen, click, or panel that no line below needs stays off the demo path.

## The one sentence

**Bid-Ready takes a small firm from two lines about itself to a bid pack it can hand over, and refuses to call anything ready until a second checker has re-read the tender.**

## Three ideas to land (and only three)

1. **The paperwork is the job.** 67.9% of Greek startups have never bid on a public contract; 55% want help with the dossier (Powergame, 2024).
2. **Honest beats hopeful.** The fit score says "good match". The tender says "not eligible alone". We show both, with the clause and page.
3. **Receipts, not vibes.** The agent's "done" is not accepted. A verifier re-reads the PDF page, and it caught a real €2,000 error.

## Script (target 2:30, hard stop 3:00)

| Time | Beat | On screen | Say (roughly) |
|---|---|---|---|
| 0:00 | Hook | Title / app home | "67.9% of Greek startups have never bid on a public contract. The paperwork is the job, and one wrong number gets you excluded." |
| 0:10 | Who you are | Click **Use demo studio**, answer the 3 questions | "Two lines about an 8-person Athens studio. We only ask what we can't work out: turnover, certificates, public projects." |
| 0:25 | Matches | Ranked list from live TED | "We searched TED, scored every open Greek IT tender with a visible formula, and this one scores 77: right CPV, Greece, three weeks to prepare." Click **Prepare bid**. |
| 0:45 | The honest answer | Eligibility table | "But a fit score isn't eligibility. The tender itself says no: five escrow-payment projects, six ISOs, €400k turnover. Each line cites the section and the page." |
| 1:10 | Next step | Greek letter (2 seconds) | "So instead of a bid they'd lose, we draft a letter in Greek to a consortium partner." |
| 1:20 | **The catch** | FAILED receipt, NOT READY banner | "TED's headline says €300,000, so a naive agent computes a €6,000 guarantee. Our verifier re-opened page 20 of the PDF: €4,000. FAILED. We don't mark it ready. That is the product." |
| 1:50 | Handover | Open the ZIP | "Letter, checklist, receipts, a calendar entry for 7 December, 14:00 Athens. A human signs on ΕΣΗΔΗΣ. We stop here." |
| 2:05 | Agents | Claude Code / Cursor: "Check eligibility on TED 769674-2026" | "Other agents can call the same six tools. They get the FAILED receipt too." |
| 2:20 | Close | Back on the receipt | "People get a pack. Agents get a receipt. Nothing is ready until it's checked." |

## Kept for questions, not the script

- Model check (Gemini 27/27 with the page, fell for €300,000 every time with only the headline)
- The fit-score breakdown pane
- Value filter, ΟΛΠΑ live extraction, Lab panel
- Answers in `docs/08-demo-and-submission.md` (Judge Q&A)

## Before recording / going live

- Delete `out/rule_cache.json` so ΚτΠ starts at 77.
- Re-check the ranking the same morning; ΚτΠ still shows if it drops out of the top 8.
- `pytest -q` green (golden test).
- MCP server approved in the client; terminal fallback ready.
