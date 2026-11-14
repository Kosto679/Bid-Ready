# Scoring

`score_tenders` must use a simple, visible formula on **TED metadata plus the company profile**. Do not read `requirements.json` here. Only the ΚτΠ tender has that file, and the other shortlist notices would have nothing to score against.

**Exception (added Sat 14 Nov):** when a tender's own turnover rule has been read from its text and the verifier marked it VERIFIED (via Prepare bid), the value factor uses that rule instead of the rule of thumb below: `have / need`, where `have` is the 3-year total for a "total" rule or the total ÷ 3 for a "yearly average" rule. The UI labels which one was used. Rules are stored in `app/rule_cache.py`, never taken from `requirements.json` directly.

## Inputs

From each TED notice:

- `classification-cpv` (one or more codes)
- estimated / procedure-level value, if TED returns it (for 769674-2026 this is €300,000, which includes the option — that is a known TED headline figure, not the €200,000 initial budget used in eligibility)
- `place-of-performance` (Greek NUTS codes start with `EL`; country may be `GRC`)
- `deadline-receipt-tender-date-lot` and `deadline-receipt-tender-time-lot`

From the company profile:

- `cpv_codes` (likely codes from onboarding)
- `turnover_2023_2025_total_eur` (3-year total; may be null)
- `location` / `nuts_or_country`
- "today" for days-to-deadline (use Europe/Athens)

## Formula (implement exactly this)

Fit score is 0–100, equal weights on four factors, each 0–1:

```
fit_score = round(100 * (0.25 * cpv + 0.25 * value_fit + 0.25 * place + 0.25 * deadline))
```

### CPV overlap (`cpv`)

Compare notice CPV codes with the profile's `cpv_codes`.

- Normalize to digits (ignore the check digit after a hyphen). A match is a shared 2-digit prefix (e.g. profile `72*` or `72000000` matches notice `72000000-5`).
- `cpv = matches / max(number of notice CPVs, 1)`.
- If the profile has no CPV codes, `cpv = 0`.

### Value versus turnover (`value_fit`)

TED's estimated value may include options. Use it anyway here — this is a coarse shortlist score, not the legal threshold.

- Let `need = 2.0 * ted_estimated_value` (a rough 200% heuristic).
- If profile turnover is null, `value_fit = 0`.
- Else `value_fit = min(1.0, turnover_2023_2025_total_eur / need)`.

### Place / NUTS (`place`)

- `1.0` if the profile country is Greece / `GRC` and the notice `place-of-performance` includes an `EL*` NUTS code or `GRC`.
- `1.0` if a more specific profile NUTS code is contained in the notice places.
- `0.0` otherwise (including missing place data).

### Days to deadline (`deadline`)

This is a **fit / feasibility** factor (more time to prepare is better), not an urgency rank.

- `days =` calendar days from today (Europe/Athens) to the deadline date. If the deadline has passed, `days = 0`.
- `deadline = min(days, 45) / 45`.
- 45 is a cap so very distant deadlines do not dominate. Document the cap in code comments and in the one-line reason if you hit it.

## Sort and reason

- Sort descending by `fit_score`. Ties: earlier deadline first, then publication number.
- `reason` is **one sentence**, in plain language, built from the four fields (not from `requirements.json` and not from model free-invention). Template:

  "CPV {matches or does not match} your profile; the TED value is {value} versus your {turnover} 3-year turnover; place is {place}; the deadline is {date} ({N} days)."

- The ΚτΠ demo tender (TED 769674-2026, TED headline value €300,000, deadline Mon 7 Dec 2026, CPV `72000000-5`, place Greece) should score **honestly**, probably low for a small-firm profile with modest turnover. Do not boost it because it is the demo case.

## What this score is not

- It is not eligibility. Eligibility is `check_eligibility`, which uses the notice rules (€200,000 basis, five escrow projects, six ISOs, and so on).
- In the demo, a low ΚτΠ score is expected. The operator then chooses it deliberately: it is the biggest and has the soonest deadline, so why is it scored low? Let's check.
