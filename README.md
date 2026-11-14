# Bid-Ready

A guided path from a two-line company profile to a checked bid pack for Greek/EU public tenders. Nothing is marked ready until an independent verifier re-reads the tender itself and issues a receipt.

**Problem.** A 2024 Powergame report found 67.9% of Greek startups have never bid on a public contract, and 55% wanted help preparing the dossier ([source](https://www.powergame.gr/start-ups-digital/1039587/i-athanati-grafeiokratia-krata-tis-ellinikes-startups-makria-apo-ta-erga-tou-dimosiou/)).

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt
copy .env.example .env            # optional: ANTHROPIC_API_KEY for LLM onboarding
pytest -q                         # golden KtP test runs fully offline
uvicorn app.main:app --port 8000  # UI at http://localhost:8000
python -m app.mcp_server          # MCP (stdio): six tools
```

Set `BIDREADY_OFFLINE=1` to skip live TED and use `data/tender-demo/ted-cache/`.

MCP clients (both configs ship in the repo; create the `.venv` first):

- **Claude Code**: `.mcp.json` at the project root. Open the project in Claude Code and approve the `bid-ready` server when asked.
- **Cursor**: `.cursor/mcp.json`. Enable `bid-ready` under Settings → MCP.

Then ask: *"Check eligibility on TED 769674-2026."* The result includes the FAILED guarantee receipt. TED calls time out after 8 s and fall back to the local cache, so the call works offline.

## What it does

| Tool | What it does |
|---|---|
| `find_tenders` | TED Search API v3 (no key), Greek IT notices; local cache fallback marks the live hop UNVERIFIED |
| `score_tenders` | Visible formula on TED metadata only: 25% CPV, 25% value vs 3-year turnover, 25% place, 25% days to deadline |
| `check_eligibility` | Rules with `meets / missing / unclear`, each citing section + PDF page + printed page, then runs the verifier |
| `draft_cover_letter` | Greek consortium-partner letter (.md + .docx), using verified figures only |
| `verify` | Re-opens the cited tender page (`text/pages.json`) or pack file; `VERIFIED / FAILED / UNVERIFIED`, idempotent |
| `build_pack` | ZIP (ASCII names): letter, checklist, `receipts.json`, `deadline.ics` (`20261207T120000Z` = 14:00 Athens). Stops; a human signs on ΕΣΗΔΗΣ |

## Demo: TED 769674-2026 (ΚτΠ), offline-capable

Demo profile: 8-person Athens studio, €350,000 3-year turnover, ISO 9001 only, two small municipal websites (no escrow).

- Verdict **not eligible**: §2.2.6.1 (five escrow-payment projects), §2.2.7 (six ISOs), §2.2.5 (turnover < €400,000 total).
- The naive extractor trusts TED's procedure-level value (`estimated-value-proc` = €300,000) and computes a €6,000 guarantee. The verifier re-reads §2.2.2.1 on PDF p27 / printed 20 and finds **€4,000** → **FAILED**, pack **NOT READY**.

**Honest note.** `data/tender-demo/769674-2026/requirements.json` is a human-curated clause index prepared before the hackathon. It tells the agent *what* to check and *where*. The verifier never grades against it; it re-opens the cited page text from the tender PDF. Fixtures and cached documents were prepared before Saturday 13:00; the code was built after (see commit times).

## Model eval (Gemini on the contest's Google Cloud)

How often does a model get the tender facts right? Gemini extracts nine facts from TED 769674-2026 (budget, both guarantees, turnover threshold, deadline, opening, escrow projects, duration, ISO count). The verifier re-reads the PDF page and grades every answer: correct, wrong, abstained, or error. The answer key is never `requirements.json`.

- **headline**: the model sees only TED metadata (the €300,000 headline). Abstaining is the right answer for most fields.
- **page**: the model sees the cited page text.
- **full**: the whole RFP text (large; opt-in).

```bash
gcloud auth application-default login       # once, with the contest account
# .env: GOOGLE_CLOUD_PROJECT=<contest project id>, GOOGLE_CLOUD_LOCATION=global, GEMINI_MODEL=<model id>
python -m app.evals --conditions headline,page --trials 3
```

Results land in `out/evals/` (JSON + Markdown) and in the UI's "Model check" panel. Every graded answer is also a receipt.

## Out of scope

Submitting on ΕΣΗΔΗΣ, fetching the ESPD `.xml`, parsing the full 137-page διακήρυξη from scratch.
