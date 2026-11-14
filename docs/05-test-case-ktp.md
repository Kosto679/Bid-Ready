# Test case: TED 769674-2026 (ΚτΠ)

Do not invent thresholds beyond this file, `data/tender-demo/769674-2026/README.md`, and `data/tender-demo/769674-2026/requirements.json`.

## Where the files live

On the Windows laptop, unzip `tender-demo.zip` into `./data/tender-demo/`.

Primary pack: `data/tender-demo/769674-2026/`

- `README.md`
- `requirements.json` (also shipped in this docs pack under the same relative path)
- `docs/` — Word διακήρυξη, signed RFP PDF, buyer-prefilled ΕΕΕΣ PDF, e-Notice PDF
- `text/` — extracted text; `rfp_compact.txt` has `---PDF pN---` markers; `pages.json` is a per-page array
- `ESCROW-ACCOUNTS.zip` — original public ZIP
- `ted-notice-769674-2026.xml`

Public sources:

- TED notice: https://ted.europa.eu/en/notice/-/detail/769674-2026
- Document ZIP: https://www.ktpae.gr/wp-content/uploads/2026/11/ESCROW-ACCOUNTS.zip
- ΚΗΜΔΗΣ open-data attachment: https://cerpp.eprocurement.gov.gr/khmdhs-opendata/notice/attachment/26PROC020137847

`requirements.json` is human-curated ground truth for this one notice, prepared as a fixture / clause index (section, `pdf_page`, `doc_page`, sometimes a quote). Use it to know what to check. The verifier must confirm cited clauses against the PDF or `text/`, not by re-reading only this JSON.

Page numbering: the RFP PDF opens with a 7-page decision. Body PDF page N is printed page N−7 (footer "X - 103"). Citations must store both. Example: §2.2.5 is PDF p33 / printed 26.

## Notice facts

- **TED:** 769674-2026 · OJ S 2026/S 215-769674
- **Buyer:** ΚΟΙΝΩΝΙΑ ΤΗΣ ΠΛΗΡΟΦΟΡΙΑΣ Μ.Α.Ε. (ΚτΠ), ΑΦΜ 999983307, Λεωφ. Συγγρού 194, 176 71 Καλλιθέα
- **Title:** Παροχή Υπηρεσιών Συντήρησης, Υποστήριξης και Παραμετροποίησης του Πληροφοριακού Συστήματος Μηχανισμού Πληρωμών Προγραμμάτων Επιδοτήσεων (Escrow Accounts) της Κοινωνίας της Πληροφορίας Μ.Α.Ε.
- **IDs:** ΑΔΑΜ 26PROC020137847 · ΑΔΑ ΨΣ8Σ469Η4Σ-ΝΛΘ · ΕΣΗΔΗΣ 589064 · CPV 72000000-5
- **Value:** €200,000 excl. VAT initial (€125,000 support + 5 × €15,000 parametrisation). +€100,000 option (50%), so €300,000 total (what TED's procedure-level value shows). €248,000 / €372,000 incl. VAT 24%.
- **Duration:** 12 months. One lot. Award: best price-quality ratio, technical 80% / price 20%.
- **Deadline:** Monday 7 Dec 2026, 14:00 Europe/Athens. Clarifications until 18 Nov 2026. Technical opening Friday 11 Dec 2026, 14:00.
- **Submission:** electronic only on ΕΣΗΔΗΣ (promitheus.gov.gr, system 589064), in Greek, with an advanced/qualified e-signature. The original paper participation guarantee must still reach Syngrou 194 before opening.

## Thresholds the checker must get right

| Rule | Correct figure | Where |
|---|---|---|
| Turnover | Sum of 2023+2024+2025 ≥ €400,000 (200% of €200,000, a 3-year total, not per year). Profitable in each of those years. | §2.2.5, PDF p33 / printed 26 |
| Experience | ≥5 public-sector escrow-payment projects in 2021–2026, including one SLA support project ≥ €200,000, plus a digital-transformation consulting project with maintenance. | §2.2.6.1, p33–34 |
| Team (do not block the demo on this; drop first if behind) | PM (12 years, master's, PM on ≥3 projects incl. a Greek public payment system); 2 senior developers (≥5 years); 2 developers (≥3 years); InfoSec officer (master's, ISO 27001 auditor, ≥20 years of which ≥10 in infosec); DPO (law degree, master's, GDPR experience). | §2.2.6.2, p34–35 |
| ISOs | Six certificates: 9001, 20000-1, 27001, 27701, 22301, 37001. In a JV, every member needs them. The notice cites editions "27001:2019" and "27701:2019" (sic) — flag, do not silently correct. | §2.2.7, p36–37 |
| Participation guarantee | €4,000 (2% of €200,000). Paper original. | §2.2.2.1, PDF p27 / printed 20 |
| Performance guarantee | €8,000 (4% of €200,000) at signature. | §4.1 p72 |

Core eligibility for the weekend covers turnover, experience, ISOs, and the participation guarantee. Drop team-CV detail if behind.

## The guarantee trap (use this, not a turnover plant)

- TED headline / procedure-level value: €300,000.
- Correct basis for the guarantee: €200,000 excl. VAT and option.
- Naive extractor: 2% × €300,000 = **€6,000**.
- Verifier, re-reading §2.2.2.1: **€4,000**.
- Receipt status: **FAILED**. Pack is not marked ready.

Do **not** plant a "€300,000 vs €400,000 turnover" error. €300,000 is a budget figure, not a turnover threshold. (200% of the TED headline would be €600,000; an annual misreading of the €400,000 total is about €133,000 a year.) Those are useful things to flag if a model invents them; they are not the arranged demo miss.

Implement the miss as a naive extractor that trusts the TED value field, not as a hidden switch.

## Other traps to flag, not "fix"

- Budget confusion: €200,000 vs €300,000 vs VAT-inclusive €248,000 / €372,000. Turnover, guarantees, and the SLA-project rule all use €200,000.
- Turnover is a 3-year **total**, not an annual figure.
- Source errors in the notice: nonexistent ISO editions ("27001:2019"), mixed sanctions-regulation numbers (2022/578 vs 2022/576), a dangling "και:" in §2.2.7, a σ4 term in a 3-criterion formula, a **different project's title** in Annex III/IV page headers, Annex IX vs VIII for data protection, mismatched fax numbers. Flag them; do not silently correct them in a form.
- Certificate freshness is mixed: some ≤3 months, some ≤30 working days.
- Paper original guarantee must arrive by the 11 Dec 2026 14:00 opening even though the bid is electronic.

## Expected verdict (demo small-firm profile)

Use an 8-person Athens software studio. Onboard with turnover, certificates, and public-sector projects in the last 5 years. In the demo, answer the projects question (e.g. "none" or "two small sites, not escrow") so experience can be `missing` rather than `unclear`.

Honest output: **not eligible**, because of clause §2.2.6.1 (five escrow-payment projects) and typically §2.2.7 (six ISOs), and turnover if the profile total is under €400,000. Add a one-line note on what a partnership / JV would need. Draft the Greek letter as consortium outreach.

Almost no SME qualifies (five escrow projects, six ISOs, a 20-year infosec officer). Do not fake an "eligible" result.

## Backup tender

If the ΚτΠ pack is too heavy, or to show partial live extraction on a tender you did not pre-annotate: Patras Port Authority (ΟΛΠΑ Α.Ε.), ΑΔΑΜ 26PROC020181047, "Σχεδιασμός και ανάπτυξη νέας πλατφόρμας εφαρμογών ΟΛΠΑ Α.Ε." €280,000 excl. VAT initial; deadline Tue 1 Dec 2026, 11:00 Europe/Athens; ΕΣΗΔΗΣ 464035. More SME-friendly (similar projects totalling ≥ €140,000, four ISOs) but fewer public annexes. A quick TED search did not confirm a TED publication number. Path: `data/tender-demo/backup-OLPA-26PROC020181047/`. Do not rebuild a full `requirements.json` for it. Live extraction of a few fields is an extra, not core.
