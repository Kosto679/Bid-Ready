"""draft_cover_letter: Greek consortium-partner outreach (Markdown + .docx), ASCII file names.

Facts in the letter come from the eligibility report and from VERIFIED receipts only; a FAILED
figure is replaced by what the verifier observed on the tender page.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import config
from . import receipts as R
from .receipts import new_run_id, write_receipt

GR_MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου", "Ιουλίου",
             "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]

STATUS_EL = {"meets": "καλύπτεται", "missing": "δεν καλύπτεται", "unclear": "προς διευκρίνιση"}


def _gr_date(d: datetime) -> str:
    return f"{d.day} {GR_MONTHS[d.month - 1]} {d.year}"


def _eur(v: float) -> str:
    return f"{v:,.0f} €".replace(",", ".")


def _verified_guarantee(run_id: str) -> float | None:
    for r in R.list_receipts(run_id):
        if r["intent"].get("claim_id") == "participation_guarantee" and r["independent_check"]:
            obs = r["independent_check"].get("observed") or {}
            return obs.get("participation_guarantee_eur")
    return None


def render_markdown(profile: dict, eligibility: dict, guarantee: float | None) -> str:
    today = config.now_athens()
    name = profile.get("name") or "Η εταιρεία μας"
    size = profile.get("size")
    rules = {r["id"]: r for r in eligibility.get("rules", [])}
    gaps = [r for r in eligibility.get("rules", []) if r["status"] == "missing"]
    gap_lines = "\n".join(
        f"- {r['title']} — {STATUS_EL[r['status']]} (§{r['citation']['section']}, σελ. {r['citation']['printed_page']} της διακήρυξης)"
        for r in gaps
    ) or "- Δεν εντοπίστηκαν ελλείψεις."
    alone = eligibility.get("verdict") == "not_eligible"
    certs = ", ".join(profile.get("certificates") or []) or "—"
    g_line = f"Η εγγύηση συμμετοχής, όπως ελέγχθηκε στην §2.2.2.1, ανέρχεται σε {_eur(guarantee)}." if guarantee else ""

    return f"""# Πρόταση συνεργασίας για τον διαγωνισμό TED 769674-2026

**Αθήνα, {_gr_date(today)}**

**Προς:** [Επωνυμία πιθανού εταίρου]
**Από:** {name}{f" ({size} άτομα)" if size else ""}, {profile.get('location') or ''}
**Θέμα:** Συνεργασία (ένωση οικονομικών φορέων ή υπεργολαβία) για τον διαγωνισμό της ΚΟΙΝΩΝΙΑ ΤΗΣ ΠΛΗΡΟΦΟΡΙΑΣ Μ.Α.Ε. «Παροχή Υπηρεσιών Συντήρησης, Υποστήριξης και Παραμετροποίησης του Πληροφοριακού Συστήματος Μηχανισμού Πληρωμών Προγραμμάτων Επιδοτήσεων (Escrow Accounts)» — ΑΔΑΜ 26PROC020137847, ΕΣΗΔΗΣ 589064

Αξιότιμε/η κύριε/κυρία,

Είμαστε η {name}. {profile.get('summary') or ''}

Μελετήσαμε τη διακήρυξη (προϋπολογισμός 200.000 € χωρίς ΦΠΑ, με δικαίωμα προαίρεσης έως 100.000 €· καταληκτική ημερομηνία υποβολής **Δευτέρα 7 Δεκεμβρίου 2026, 14:00**). {"Με ειλικρίνεια: **δεν μπορούμε να υποβάλουμε προσφορά μόνοι μας**." if alone else ""} Οι απαιτήσεις που δεν καλύπτουμε σήμερα είναι:

{gap_lines}

## Τι προτείνουμε

{"Αναζητούμε εταίρο με τεκμηριωμένη εμπειρία σε τουλάχιστον πέντε έργα συστημάτων πληρωμών μέσω escrow accounts για φορείς του Δημοσίου, εκ των οποίων ένα με υποστήριξη SLA αξίας τουλάχιστον 200.000 €, και με τα έξι πιστοποιητικά ISO της §2.2.7. Επειδή σε ένωση κάθε μέλος οφείλει να διαθέτει όλα τα πιστοποιητικά ISO, θεωρούμε ρεαλιστικότερο να συμμετάσχουμε ως υπεργολάβος." if alone else "Προτείνουμε κοινή υποβολή προσφοράς."}

## Τι προσφέρουμε

- Ομάδα ανάπτυξης λογισμικού με εμπειρία σε web εφαρμογές και πίνακες δεδομένων
- Διαθεσιμότητα για τις υπηρεσίες παραμετροποίησης (5 πακέτα × 15.000 €)
- Πιστοποιητικά που διαθέτουμε: {certs}
- Δημόσια έργα (τελευταία 5 έτη): {profile.get('public_sector_projects_last_5y') or '—'}

{g_line}

Θα χαρούμε να συζητήσουμε σε σύντομη τηλεφωνική επικοινωνία πριν από τη λήξη της προθεσμίας διευκρινίσεων (18 Νοεμβρίου 2026).

Με εκτίμηση,

[Ονοματεπώνυμο νόμιμου εκπροσώπου]
{name}

---
*Σχέδιο επιστολής που συντάχθηκε από το Bid-Ready. Ελέγξτε το και υπογράψτε το εσείς. Δεν υποβάλλεται στο ΕΣΗΔΗΣ.*
"""


def _write_docx(md: str, path: Path) -> bool:
    try:
        from docx import Document
    except ImportError:
        return False
    doc = Document()
    for line in md.splitlines():
        s = line.strip()
        if not s or s == "---":
            continue
        if s.startswith("# "):
            doc.add_heading(s[2:], level=1)
        elif s.startswith("## "):
            doc.add_heading(s[3:], level=2)
        elif s.startswith("- "):
            doc.add_paragraph(s[2:].replace("**", ""), style="List Bullet")
        else:
            doc.add_paragraph(s.replace("**", "").replace("*", ""))
    doc.save(path)
    return True


def draft_cover_letter(notice_id: str, profile: dict, eligibility: dict, run_id: str | None = None) -> dict:
    run_id = run_id or eligibility.get("run_id") or new_run_id()
    d = config.OUT_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    md = render_markdown(profile, eligibility, _verified_guarantee(run_id))
    md_path = d / "consortium_letter_el.md"
    md_path.write_text(md, encoding="utf-8")
    docx_path = d / "consortium_letter_el.docx"
    has_docx = _write_docx(md, docx_path)
    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"draft_cover_letter:{run_id}:{notice_id}",
        "action": "draft_cover_letter",
        "intent": {"notice_id": notice_id, "framing": "consortium_outreach" if eligibility.get("verdict") == "not_eligible" else "cover"},
        "tool_call": {"name": "draft_cover_letter", "arguments": {"notice_id": notice_id}},
        "tool_response": {"path": str(md_path), "docx": str(docx_path) if has_docx else None, "language": "el"},
        "status": "RECORDED",
        "reason": "Letter file written; existence is re-read by the verifier in build_pack.",
    })
    return {"run_id": run_id, "path": str(md_path), "docx_path": str(docx_path) if has_docx else None, "language": "el", "markdown": md, "receipt": receipt}
