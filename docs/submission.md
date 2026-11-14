# Bid-Ready: submission project details (draft)

Draft for the Gen AI Summit Hackathon form. Edit the bracketed parts; check figures against the final run before submitting.

## Name

Bid-Ready

## One-liner

From two lines about your company to a checked bid pack for Greek public tenders, and nothing is marked ready until an independent verifier re-reads the tender itself.

## Problem

Greek SMEs mostly stay out of public procurement. A 2024 Powergame report found 67.9% of Greek startups have never bid on a public contract, and 55% wanted help preparing the dossier. Tender documents run past 100 pages, mix three different "budgets", and hide hard eligibility rules in numbered clauses. An LLM can summarise them, but it will also confidently repeat the wrong number.

## What it does

1. **Onboard**: two typed lines become a company profile; it asks only for turnover, certificates and public-sector projects.
2. **Match**: live search of TED (EU tenders), ranked by a visible fit formula on TED metadata: CPV, value vs turnover, place, days to deadline.
3. **Check eligibility**: every rule comes back as meets / missing / unclear, citing the clause, PDF page and printed page.
4. **Verify**: a separate verifier re-opens each cited page and grades every claim VERIFIED / FAILED / UNVERIFIED, with an idempotent receipt.
5. **Hand over**: a Greek consortium-partner letter, an eligibility checklist, the receipts and a deadline calendar file, zipped. A human signs and submits on ΕΣΗΔΗΣ; we stop there.

The same six tools are exposed over MCP, so other agents get a receipt, not a vibe.

## Demo: TED 769674-2026 (Κοινωνία της Πληροφορίας, escrow-payments platform)

- An 8-person Athens software studio is honestly **not eligible**: it lacks five public escrow-payment projects (§2.2.6.1) and six ISO certificates (§2.2.7), and its turnover is under the €400,000 three-year total (§2.2.5). The letter becomes outreach to a consortium partner.
- TED's headline value is €300,000 (it includes a €100,000 option). A naive extractor computes a 2% participation guarantee of €6,000. The verifier re-reads §2.2.2.1 on PDF page 27 and finds €4,000. **FAILED**, so the pack is handed over as NOT READY.

## Model eval on the contest's Google Cloud

We asked Gemini (gemini-3.8-flash on Vertex AI) for nine facts from this tender and let the verifier grade each answer against the PDF page. 3 trials each:

| Model sees | Correct | Wrong | Abstained |
|---|---|---|---|
| The cited PDF page | 27 / 27 | 0 | 0 |
| Only the TED headline | 3 | 3 | 21 |

Every wrong answer was the same trap: given the headline, Gemini reported €300,000 as the initial budget (the page says €200,000). The verifier caught all three.

## How it's built

Python 3.11+ · FastAPI · MCP Python SDK (FastMCP, stdio) · SQLite receipts · TED Search API v3 · Gemini on Vertex AI (Google Cloud) for profile reading, CPV codes, the letter rewrite and the eval harness · python-docx. 39 offline tests, including a golden end-to-end test on TED 769674-2026.

## Honest notes

- `requirements.json` for this tender is a human-curated clause index, prepared before the start. It tells the agent what to check and where. The verifier never grades against it; it re-reads the page text extracted from the tender PDF.
- Fixtures and cached documents were prepared before Saturday 13:00; all code was written after (see commit times).
- Out of scope: submitting on ΕΣΗΔΗΣ, the ESPD XML, parsing arbitrary tenders end to end.

## What's next

MCP tools that scan tenders with filters across TED and the Greek ΚΗΜΔΗΣ register, then index and check any of them automatically (starting with the ΟΛΠΑ backup), pre-filling the ΕΕΕΣ/ESPD, and a "what you're missing" path linked to the official gov.gr procedures.

## Links

- Repo: [private GitHub repo; add access for judges if required]
- Video: [link]
- Team: [names]
