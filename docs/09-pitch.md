# Demo video: script and shot list

The submission video. About 2:30, hard stop 3:00. No MCP beat. Every figure below was checked on screen on Sun 15 Nov.

## The one sentence

**Bid-Ready takes a small firm from two lines about itself to a bid pack it can hand over, and refuses to call anything ready until a second checker has re-read the tender.**

## The story in four beats

1. **The problem.** 67.9% of Greek startups have never bid on a public contract (Powergame, 2024).
2. **A "no", told honestly.** ΚτΠ scores 87 on paper, but its own rules say you can't bid alone.
3. **The catch.** Our own first reading got the guarantee wrong (€6,000). The verifier re-read page 27: €4,000.
4. **A "yes", ready to hand over.** 774438-2026, a tender nobody annotated: read live, "You can bid on this one", pack READY.

## Shot list

| Time | Screen | Do | Say (roughly) |
|---|---|---|---|
| 0:00 | Home, logo | Nothing | "67.9% of Greek startups have never bid on a public contract. The paperwork is the job, and one wrong number gets you excluded. Bid-Ready does that paperwork, and checks itself." |
| 0:12 | Tell us who you are | **Use demo studio**, scroll past the CPV codes to the three answers | "Two lines about an 8-person Athens studio. It works out what they sell, and asks only what it can't: turnover, certificates, public projects." |
| 0:27 | Open Greek IT tenders | **Find matching tenders** | "It searches TED live, scores all 49 open Greek IT tenders with a formula you can see, and shows the best eight." |
| 0:37 | Fit report (ΚτΠ, 87) | Click the top tender | "This one is a strong fit on paper. But a fit score isn't eligibility." **Check eligibility →** |
| 0:47 | Can you bid? ΚτΠ | Pause on the verdict, then point at ✗ rows | "The tender's own rules say no: five escrow-payment projects, six ISO certificates. Every line links to its page in the PDF. You could still join as a subcontractor." |
| 1:05 | Scroll to "How we checked our own reading" | Stop on "Caught a wrong figure" | "And here's the part that matters. Our first reading put the guarantee at €6,000, 2% of the €300,000 headline on TED. The verifier re-read page 27: €4,000. We use €4,000, and the pack stays 'needs review' until a person sees it." |
| 1:30 | Same screen, Greek letter | Scroll down to the letter (2–3 s) | "Since they can't bid alone, it drafts a letter in Greek to a possible consortium partner." |
| 1:38 | Back → tender list | Scroll to **774438-2026** (Asterousia digital repository, €125k), open, **Check eligibility →** | "Now one they can win. Nobody annotated this tender. We found its document in the Greek procurement register and read it live." |
| 1:52 | Can you bid? 774438 | Point at ✓ turnover, ✓ ISO 9001, ? team | "Turnover ✓, ISO ✓. The team is something only the company knows." |
| 2:00 | Team row | **Answer**, tick the three roles, **Save and re-check** | Verdict turns to **"You can bid on this one."** "Guarantee €2,502, deadline 14 December, every figure with its page." |
| 2:12 | Handover | **Build the pack →**, **Build handover ZIP** | "READY. A checklist that starts with what to do and by when, the tender, the receipts, a calendar entry for the deadline." |
| 2:25 | Same | Hold on "Bid-Ready does not submit" in the to-do | "A human signs and submits on ΕΣΗΔΗΣ. We stop there. Nothing is ready until it's checked." |

## Recording setup

- **Window:** 1920×1080, browser zoom 125% (the app is a narrow column; at 100% the text is small on video). Hide the bookmarks bar, close other tabs.
- **Light mode.** The navy logo and red/green verdicts read best on light.
- **Warm-up run first**, then reload and record. It fills the caches: TED search, the 774438 rule read (Gemini varies run to run; the cached read in `out/rules_read/` is a verified one), and the Greek letter (about 12 s of Gemini in the background).
- **Check 774438 before recording:** turnover ✓, ISO 9001 ✓, team "?" with an **Answer** link, guarantee €2,502. If any differ, re-run until it matches or use the cached read.
- **Record the screen first, then the voice.** Cut dead air in the edit; the clicks are fast, so the voice sets the pace.
- **If TED is down,** the search falls back to the local cache and says so in the summary line. The rest works offline.

## Kept for questions, not the video

Model check (Gemini 27/27 with the page; it fell for €300,000 with only the headline), Oumi second opinion, Firecrawl website onboarding, value filter, receipts wall ("Show every check"), MCP tools. Answers: `docs/08-demo-and-submission.md`, Judge Q&A.
