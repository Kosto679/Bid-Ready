# Bid-Ready demo tender: TED 769674-2026 (ΚτΠ Μ.Α.Ε., Escrow Accounts)

**TED:** https://ted.europa.eu/en/notice/-/detail/769674-2026 (OJ S 2026/S 215-769674)
**Buyer:** ΚΟΙΝΩΝΙΑ ΤΗΣ ΠΛΗΡΟΦΟΡΙΑΣ Μ.Α.Ε. (ΚτΠ), ΑΦΜ 999983307, Λεωφ. Συγγρού 194, Καλλιθέα
**Title:** Παροχή Υπηρεσιών Συντήρησης, Υποστήριξης και Παραμετροποίησης του ΠΣ Μηχανισμού Πληρωμών Προγραμμάτων Επιδοτήσεων (Escrow Accounts)
**IDs:** ΑΔΑΜ διακήρυξης 26PROC020137847 · ΑΔΑ ΨΣ8Σ469Η4Σ-ΝΛΘ · ΕΣΗΔΗΣ α/α 589064 · CPV 72000000-5
**Value:** €200,000 excl. VAT initial (€125k support + 5 × €15k parametrisation packages); +€100k option (50%), so €300k total; €248k / €372k incl. VAT 24%
**Duration:** 12 months · **Lots:** one · **Award:** best price-quality ratio, technical 80% / price 20%
**Deadline:** **Mon 07-12-2026 14:00 (Athens)** · clarifications until 18-11-2026 · technical opening Fri 11-12-2026 14:00
**Submission:** electronic only on ΕΣΗΔΗΣ (promitheus.gov.gr), in Greek, with an advanced/qualified e-signature. The original paper guarantee must be delivered physically.

## Files
- `docs/ESCROW-ACCOUNTS/`: the public ZIP from ktpae.gr (`https://www.ktpae.gr/wp-content/uploads/2026/11/ESCROW-ACCOUNTS.zip`)
  - `RFP_…pdf`: signed διακήρυξη, 137 PDF pages, with the ESPD at pp. 111–137. The same document is also served by the ΚΗΜΔΗΣ open-data API at `…/khmdhs-opendata/notice/attachment/26PROC020137847`.
  - `RFP_ESCROW_ACCOUNTS_2026.docx`: **editable Word version**, so you can fill annexes straight into it
  - `ΕΕΕΣ_…pdf`: buyer-prefilled ESPD (27 pages)
  - `E-Notice…pdf`: the EU contract notice (10 pages)
- `ESCROW-ACCOUNTS.zip` (original) · `ted-notice-769674-2026.xml` (eForms XML)
- `text/`: extracted text. `rfp_compact.txt` has `---PDF pN---` markers. `pages.json` is a per-page array. Also `espd.txt`, `enotice.txt`, `RFP_docx.txt`.
- `requirements.json`: structured requirements. Every item has a citation `{file, section, pdf_page, doc_page}`.
- `build_requirements.py`: the source for the JSON

**Page numbering trap:** the RFP PDF opens with a 7-page decision. Body PDF page N is printed page N−7 (footer "X - 103"). The citations give both.

## Required documents/forms
**A. Agent can fill (human then signs digitally)**
| Doc | Greek | Source |
|---|---|---|
| ESPD: Parts II, III, **IV only section α**, VI | ΕΕΕΣ (Παρ. ΙΙ) | 2.2.9.1 p38–39; 2.4.3.1 p56–57; Παρ. ΙΙ p100 |
| Optional ESPD clarification declaration | Συνοδευτική υπεύθυνη δήλωση | 2.4.3.1α p56 |
| Russia-sanctions declaration | ΥΔ Καν. 833/2014 (Παρ. VI) | 2.2.1 p26–27; 2.4.3.1γ p56; p105 |
| Technical offer (fixed TOC, financial tables **without prices**) | Τεχνική Προσφορά (Παρ. IV) | 2.4.3.2 p57–58; p103 |
| Financial offer table (125,000 + 5×15,000) | Οικονομική Προσφορά (Παρ. V) | 2.4.4 p58; p104 |
| Similar-projects list (5-year template) | Κατάλογος συναφών έργων | Β.4 3.1 p44 |
| Team tables (own/subcontractor/external, person-months, %) | Πίνακες Ομάδας Έργου | Β.4 4.1 p45–46 |
| CVs | Βιογραφικά (Παρ. ΙΙΙ) | Β.4 4.2 p46; p101–102 |
| Pre-filled bank text for the guarantees | Εγγυητικές (Παρ. VII) | p106–107 |
| JV agreement / third-party capacity commitment (only if used) | Συμφωνητικό ένωσης / δέσμευση τρίτου | Β.8–Β.9 p48 |

**B. Agent drafts, human signs, swears or obtains**
- Declarations (υπεύθυνες δηλώσεις): social-insurance bodies (Β.1β ii); no final judgment on taxes or contributions (Β.1β iii); other 2.2.3.3 grounds (Β.1δ); no horizontal exclusion (Β.1ε); Annex IX integrity (Β.1στ). All are on p41–42 and must be dated **after** the invitation to submit supporting documents (Β.11, p49).
- **Sworn affidavit** (ένορκη βεβαίωση) from the legal rep on bribery convictions, under ν.5090/2024 (Β.1ζ p42). It is made before a notary or court and must be ≤3 months old.
- Cooperation declarations from external collaborators and subcontractors (Β.4 p46; Β.10 p48)

**C. Certificates a human must get (most are needed only from the provisional contractor, §3.2)**
- Criminal record extract, ≤3 months (Β.1α p41)
- Tax clearance from ΑΑΔΕ and insurance clearance from e-ΕΦΚΑ: valid at submission, otherwise ≤3 months (Β.1β p41)
- Single certificate of judicial solvency (Ενιαίο Πιστοποιητικό Δικαστικής Φερεγγυότητας) from the court of first instance; GEMI certificate that the company is not dissolved; Taxisnet "Στοιχεία Μητρώου" printout (Β.1γ p42)
- GEMI registration ≤30 **working** days (Β.2 p43); GEMI current representation ≤30 working days, plus general certificate of changes ≤3 months (Β.6 p46–47)
- Financial statements 2023–2025, or a draft 2025 balance sheet plus an e-signed turnover declaration (Β.3 p43–44)
- Good-execution certificates or acceptance protocols from public clients (Β.4 p44)
- Six ISO certificates (2.2.7 p36; Β.5 p46)
- **Participation guarantee €4,000**, paper original (2.2.2.1 p27); **performance guarantee €8,000** = 4% × €200k at signature (4.1 p72)

## Selection criteria (all "on pain of exclusion")
- **Turnover:** the **sum** of 2023+2024+2025 must be ≥ 200% of the budget excl. VAT and excl. option, i.e. **≥ €400,000 total** (2.2.5 §1, PDF p33 / printed 26)
- **Profitable** in each of the 3 years (2.2.5 §2, p33)
- **Experience 2021–2026** (2.2.6.1, p33–34):
  - ≥ **5** public-sector **escrow-account payment system** projects. Each must include ΓΓΠΣΨΔ identity interoperability, payment-request processing, links to all Greek SSM banks, reporting, and transaction documents.
  - ≥1 of them must be SLA-based production support with a budget ≥100% of this one (**≥ €200k**).
  - Plus ≥1 digital-transformation consulting project with maintenance.
- **Team** (2.2.6.2, p34–35): PM with 12 years' experience and a master's, who has been PM on ≥3 projects incl. a Greek public payment system; 2 senior developers (≥5 years); 2 developers (≥3 years); InfoSec officer (master's, ISO 27001 auditor, ≥20 years of which ≥10 in infosec, ≥2 listed certifications such as CISA or CISM); DPO (law degree, master's, ≥10 years of which 5 in GDPR, DPO certification). Experience counts only after the degree.
- **ISO** (2.2.7, p36–37): 9001:2015, 20000-1:2018, "27001:2019" (sic), "27701:2019" (sic), 22301:2019, 37001:2016. Accredited (ΕΣΥΔ or international). In a JV, **every member** needs them.
- **Exclusion grounds:** 2.2.3 (p28–32). ESPD Part III A–C as pre-filled; Part III D has none selected; Russia rule in 2.2.1 §2.
- **Evaluation:** K1 30%, K2 40%, K3 30%, scored 100–150 each, and below 100 is rejected. A = 0.8·T/Tmax + 0.2·Omin/O (2.3, p50–51).

## Traps
1. **Which budget?** €200k vs €300k vs €372k. The turnover, guarantee and SLA-project rules all use **€200k**. TED's procedure-level value shows €300k.
2. **Turnover is a 3-year total**, not an annual figure.
3. **Validity windows:** ≤3 months, ≤30 *working* days, declarations dated after the invitation, and the ESPD signed inside 06-11 to 07-12-2026.
4. **Offer validity** is 12 months from the day after the deadline. The guarantee must run ≥30 days beyond that, which I derive as about 06-01-2028.
5. **Paper original guarantee**, even though submission is electronic. It must arrive by the 11-12-2026 14:00 opening.
6. **No prices** in the technical envelope.
7. **Signatures:** every PDF must be e-signed, including the ΕΣΗΔΗΣ summary printouts.
8. **Errors in the source itself:** see `traps.source_errors` in the JSON.
   - ISO editions that don't exist
   - Regulation 2022/578 vs 2022/576
   - a dangling "…και:" in 2.2.7 with no list after it
   - a σ4 term in a 3-criterion formula
   - a **different project's title** in the Annex III/IV page headers
   - Annex IX vs VIII for data protection
   - a stray URL
   - mismatched fax numbers
9. **Wired criteria:** almost no SME qualifies. The honest output is "not eligible because of clause X" or "JV needed".

## Not obtained
- The ESPD **.xml** template is only on ΕΣΗΔΗΣ (system 589064, a JS-only page, not in the ZIP). Use the PDF ESPD, or generate XML via espdint.
- Any clarifications or amendments posted on ΕΣΗΔΗΣ after 06-11-2026 are not included. ΚΗΜΔΗΣ open data has an `amendsNoticeRefNo` field to watch.
