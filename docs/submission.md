# Bid-Ready: submission project details (draft)

Draft for the Gen AI Summit Hackathon form. Edit the bracketed parts; check figures against the final run before submitting.

## Name

Bid-Ready

## One-liner

From two lines about your company to a checked bid pack for Greek public tenders, and nothing is marked ready until an independent verifier re-reads the tender itself.

## Who it's for

Small Greek companies (a 5–50 person software studio, an engineering firm, a consultancy) that could deliver public contracts but never bid, because nobody has time to read a 137-page tender.

## Problem

Greek SMEs mostly stay out of public procurement. A 2024 Powergame report found 67.9% of Greek startups have never bid on a public contract, and 55% wanted help preparing the dossier. Tender documents run past 100 pages, mix three different "budgets", and hide hard eligibility rules in numbered clauses. An LLM can summarise them, but it will also confidently repeat the wrong number.

## What it does

1. **Onboard**: two typed lines become a company profile; it asks only for turnover, certificates and public-sector projects.
2. **Match**: live search of TED (EU tenders), ranked by a visible fit formula on TED metadata: CPV, value vs turnover, place, days to deadline.
3. **Check eligibility**: every rule comes back as meets / missing / unclear, citing the clause, PDF page and printed page.
4. **Verify**: a separate verifier re-opens each cited page and grades every claim VERIFIED / FAILED / UNVERIFIED, with an idempotent receipt.
5. **Hand over**: a Greek consortium-partner letter, an eligibility checklist, the receipts and a deadline calendar file, zipped. A human signs and submits on ΕΣΗΔΗΣ; we stop there.

The same six tools are exposed over MCP, so other agents get a receipt, not a vibe.

## Demo: one tender you can't win alone, one you can

Demo company: an 8-person Athens software studio, €400,000 turnover over 2023–25, ISO 9001, two small municipal websites.

**TED 769674-2026 (Κοινωνία της Πληροφορίας, escrow-payments platform): not alone.**
- The studio meets the turnover rule (€400,000 total, §2.2.5), but lacks five public escrow-payment projects (§2.2.6.1) and six ISO certificates (§2.2.7). The verdict says so, and that it could join as a subcontractor (§2.2.9.2 B.10). The Greek letter becomes outreach to a consortium partner.
- TED's headline value is €300,000 (it includes a €100,000 option). A naive extractor computes a 2% participation guarantee of €6,000. The verifier re-reads §2.2.2.1 on PDF page 27, finds €4,000 and corrects it; the pack stays "needs review" until a person sees it.

**TED 774438-2026 (Asterousia biosphere digital repository, €125k): yes.**
- Nobody annotated this tender. Bid-Ready found its document in ΚΗΜΔΗΣ, read it, and verified each rule against the PDF: average yearly turnover ≥ €125,101 (the studio has ≈ €133,000), ISO 9001 (held), and a named team of a project manager, an archaeologist and a photographer. The studio declares the team (contracted specialists), and the verdict becomes "You can bid on this one", with the €2,502 guarantee and the 14 Dec deadline listed.

## Sponsor tools we used

- **Firecrawl**: onboarding from a company website (home page plus up to 3 relevant pages). Every fact taken from the site keeps an exact quote and its page, checked by code; turnover is always asked.
- **Oumi Iris decision model**: an independent second opinion. It judges meaning-based rules (past projects, named team) for the company, shown as "Second opinion (Oumi)", and checks each sentence of the Greek letter rewrite against the fact-checked draft (one unsupported sentence and the draft is kept). Both write receipts; neither can make a verdict ready on its own.
- **Google Cloud (Gemini on Vertex AI)**: reads the profile and CPV codes, reads the rules of tenders nobody annotated, rewrites the Greek letter, and powers the model eval. Every figure and quote goes through the verifier.

## Model eval on the contest's Google Cloud

We asked Gemini (gemini-3.8-flash on Vertex AI) for nine facts from this tender and let the verifier grade each answer against the PDF page. 3 trials each:

| Model sees | Correct | Wrong | Abstained |
|---|---|---|---|
| The cited PDF page | 27 / 27 | 0 | 0 |
| Only the TED headline | 3 | 3 | 21 |

Every wrong answer was the same trap: given the headline, Gemini reported €300,000 as the initial budget (the page says €200,000). The verifier caught all three.

## How it's built

Python 3.11+ · FastAPI · MCP Python SDK (FastMCP, stdio) · SQLite receipts · TED Search API v3 · ΚΗΜΔΗΣ open data · Firecrawl (website onboarding) · Oumi (second opinion) · Gemini on Vertex AI (Google Cloud) for profile reading, CPV codes, the letter rewrite and the eval harness · python-docx. 74 offline tests, including a golden end-to-end test on TED 769674-2026.

## Honest notes

- `requirements.json` for this tender is a human-curated clause index, prepared before the start. It tells the agent what to check and where. The verifier never grades against it; it re-reads the page text extracted from the tender PDF.
- Fixtures and cached documents were prepared before Saturday 13:00; all code was written after (see commit times).
- Out of scope: submitting on ΕΣΗΔΗΣ, the ESPD XML, parsing arbitrary tenders end to end.

## What's next

MCP tools that scan tenders with filters across TED and the Greek ΚΗΜΔΗΣ register, then index and check any of them automatically (starting with the ΟΛΠΑ backup), pre-filling the ΕΕΕΣ/ESPD, and a "what you're missing" path linked to the official gov.gr procedures.

## Links

- Repo: https://github.com/Kosto679/Bid-Ready (public)
- Video (1 min, YouTube unlisted): https://youtu.be/0C5STIg84WE
- Team: [names]
