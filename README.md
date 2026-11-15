<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="web/brand/logo-dark.svg">
    <img src="web/brand/logo-light.svg" alt="Bid-Ready" width="420">
  </picture>
</p>

<p align="center"><b>From two lines about your company to a checked bid pack for Greek public tenders.<br>Nothing is marked ready until an independent verifier re-reads the tender itself.</b></p>

<p align="center"><a href="https://youtu.be/0C5STIg84WE">▶ 1-minute demo video</a></p>

## Who it's for

Small Greek companies (a 5–50 person software studio, an engineering firm, a consultancy) that could deliver public contracts but never bid, because nobody on the team has time to read a 137-page tender.

## The problem

A 2024 Powergame report found **67.9% of Greek startups have never bid on a public contract**, and 55% wanted help preparing the dossier ([source](https://www.powergame.gr/start-ups-digital/1039587/i-athanati-grafeiokratia-krata-tis-ellinikes-startups-makria-apo-ta-erga-tou-dimosiou/)).

Tenders are long PDFs that mix several "budgets" and hide hard eligibility rules in numbered clauses. One wrong figure (a guarantee, a turnover threshold) gets a bid excluded. A chatbot can summarise a tender, but it will also confidently repeat the wrong number.

## The solution

Bid-Ready walks a company from a short profile to a bid pack a human can sign:

1. **Onboard.** Two typed lines or a website become a profile with CPV codes. It asks only what it can't work out: turnover, certificates, public-sector projects.
2. **Match.** A live search of TED (EU tenders), ranked by a visible fit formula: CPV, value vs turnover, place, days to deadline.
3. **Read the rules.** For each tender, every eligibility rule comes back ✓ / ✗ / ? with the clause and the PDF page, plus what you'd have to provide (guarantee, documents, deadline).
4. **Verify.** A separate verifier re-opens each cited page and grades every figure and quote: `VERIFIED`, `FAILED` or `UNVERIFIED`. Each check is a receipt in SQLite. A pack is never "ready" while a check has failed.
5. **Hand over.** A ZIP: a to-do checklist, the tender, the receipts, a deadline calendar file and, where relevant, a Greek letter to a consortium partner. A human signs and submits on ΕΣΗΔΗΣ. **Bid-Ready stops there.**

## The demo: one "no", one "yes"

Demo company: Pixelridge, an 8-person Athens software studio, €400,000 turnover over 2023–25, ISO 9001, two small municipal websites.

**TED 769674-2026 (Κοινωνία της Πληροφορίας, escrow-payments platform): you can't bid alone.**
- Fit score 87 on paper. But the tender needs five public escrow-payment projects (§2.2.6.1, p33) and six ISO certificates (§2.2.7, p36). Turnover is met (€400,000, §2.2.5). The verdict says so, and that the studio could join as a subcontractor. The Greek letter becomes outreach to a consortium partner.
- **The catch.** TED's headline value is €300,000 (it includes a €100,000 option). Our first reading took 2% of that: a €6,000 participation guarantee. The verifier re-read §2.2.2.1 on PDF page 27 and found **€4,000**. The figure is corrected and the pack stays "needs review" until a person sees it.

**TED 774438-2026 (Asterousia biosphere digital repository, €125k): you can bid.**
- Nobody annotated this tender. Bid-Ready found its document in **ΚΗΜΔΗΣ** (the Greek public procurement register), read the rules with Gemini, and verified each quote against the PDF: yearly turnover ≥ €125,101 ✓ (p16), ISO 9001 ✓ (p17), a named team ?.
- The studio declares the team. The verdict becomes **"You can bid on this one"**, with the €2,502 guarantee (p11) and the 14 Dec 15:00 deadline. The pack comes back **READY**.

## Why trust it: receipts, not vibes

- **The verifier is independent of the reader.** It re-opens the cited page text extracted from the PDF and checks the quote is there and the figure matches. It never grades against our own fixtures.
- **We measured the trap.** Gemini (gemini-3.8-flash on Vertex AI), asked for nine facts from TED 769674-2026, 3 trials each, graded by the verifier:

  | Model sees | Correct | Wrong | Abstained |
  |---|---|---|---|
  | The cited PDF page | 27 / 27 | 0 | 0 |
  | Only the TED headline | 3 | 3 | 21 |

  Every wrong answer was the same trap: €300,000 reported as the budget (the page says €200,000).
- **Second opinion.** The Oumi Iris decision model independently judges "does the company meet this rule?" and every sentence of the letter; disagreements are flagged, not hidden.

## Sponsor tools we used

| Sponsor | What it does in Bid-Ready | Where |
|---|---|---|
| **Firecrawl** | Reads a company's website (home page plus up to 3 relevant pages: about, team, services, projects, certificates) so onboarding can start from a URL instead of typing. Every fact we take from the site keeps an exact quote and its page, and the code checks the quote is really there; anything the site doesn't say (turnover always) is asked. | `app/website.py`, "Or read your website" on the first screen |
| **Oumi Iris** decision model | A second, independent model for the judgement calls code can't check. (1) For meaning-based rules (past projects, named team) it answers "does this company meet the rule?" with a probability, shown next to our own reading as "Second opinion (Oumi)". (2) It checks each sentence of Gemini's Greek letter rewrite against the fact-checked draft; one unsupported sentence and we keep the draft. Both write receipts; neither can make a verdict "ready" on its own. | `app/oumi.py`, `app/eligibility.py`, `app/letter.py` |
| **Google Cloud** (Gemini on Vertex AI) | Reads the profile and CPV codes, reads the eligibility rules of tenders nobody annotated (774438-2026), rewrites the Greek letter, and powers the model eval above. Every figure and quote it returns goes through the verifier. | `app/gemini.py`, `app/rules.py`, `app/evals.py` |

All three are optional: without keys the app falls back to rule-based paths and cached readings, so the demo and tests run offline.

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt
copy .env.example .env            # optional keys; everything has an offline fallback
pytest -q                         # 74 tests, including a golden end-to-end test; all offline
uvicorn app.main:app --port 8000  # open http://localhost:8000, click "Use demo studio"
```

- **Offline:** set `BIDREADY_OFFLINE=1`. TED search and both demo tenders run from `data/tender-demo/` (cached TED notices, ΚΗΜΔΗΣ documents, extracted page text). Live calls time out after 8 s and fall back to the cache, labelled as such.
- **Optional keys** (`.env`, never committed): `GOOGLE_CLOUD_PROJECT` for Gemini on Vertex AI (`gcloud auth application-default login`), `FIRECRAWL_API_KEY` to read a company website, `OUMI_API_KEY` + `OUMI_PROJECT_ID` for the second opinion.

### For agents: MCP

`python -m app.mcp_server` (stdio) exposes eight tools: `find_tenders`, `scan_khmdhs`, `read_rules`, `score_tenders`, `check_eligibility`, `draft_cover_letter`, `verify`, `build_pack`. Configs ship for Claude Code (`.mcp.json`) and Cursor (`.cursor/mcp.json`). Ask *"Check eligibility on TED 769674-2026"*: the result includes the corrected guarantee and its receipt.

## Built with

Python · FastAPI · MCP Python SDK (FastMCP) · SQLite · **Gemini on Vertex AI** (profile reading, rule reading, letter, model eval) · **TED Search API v3** · **ΚΗΜΔΗΣ** open data · **Firecrawl** (website onboarding) · **Oumi Iris** (second opinion, letter claim check) · python-docx

```
app/        main.py (API + UI), agent.py (flow), ted.py, khmdhs.py, scoring.py, rules.py,
            eligibility.py, verifier.py, receipts.py, letter.py, pack.py, mcp_server.py, evals.py
web/        index.html (one-page UI), brand/ (logo)
tests/      74 offline tests
data/       cached tenders and extracted page text for the demo
docs/       design notes: scope, architecture, verifier, scoring, demo script
```

## Honest notes

- **Hand-made index for one tender.** `data/tender-demo/769674-2026/requirements.json` is a human-curated clause index prepared before the hackathon. It tells the agent what to check and where; the verifier never grades against it. The second demo tender (774438) has no index: its rules are read live and verified.
- **Prepared before, built during.** Fixtures and cached documents were prepared before Saturday 13:00; the code was written after (see commit times).
- **We don't submit.** Submitting on ΕΣΗΔΗΣ, signing, and fetching the ESPD XML are out of scope. A human signs.
- **Gemini's reading varies run to run.** A reading is only used once the verifier has confirmed its quotes; unconfirmed rules show as "?".

## What's next

Scan TED and ΚΗΜΔΗΣ continuously for a company's profile; pre-fill the ΕΕΕΣ/ESPD; for each missing document (e.g. tax clearance), link the official gov.gr procedure.
