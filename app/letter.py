"""draft_cover_letter: Greek consortium-partner outreach, specific to the tender (Markdown + .docx).

1. A deterministic Greek draft is built from structured facts only: the tender's scope and figures
   as read from the RFP pages, VERIFIED receipts (a FAILED figure is replaced by what the verifier
   observed), the eligibility gaps, and the profile's capabilities mapped onto the tender's work.
   No free English text from the profile is pasted in.
2. Optionally Gemini rewrites it into more natural Greek. A fact check then rejects the rewrite if
   it introduces any number not in the draft or profile, or English prose; the draft is used instead.
Both outcomes leave a receipt.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import config
from . import receipts as R
from .receipts import new_run_id, write_receipt

GR_MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου", "Ιουλίου",
             "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]

# city -> (accusative with article, for "με έδρα ..."; nominative, for the date line)
CITY_EL = {"athens": ("την Αθήνα", "Αθήνα"), "thessaloniki": ("τη Θεσσαλονίκη", "Θεσσαλονίκη"), "patras": ("την Πάτρα", "Πάτρα"),
           "heraklion": ("το Ηράκλειο", "Ηράκλειο"), "ioannina": ("τα Ιωάννινα", "Ιωάννινα"), "larissa": ("τη Λάρισα", "Λάρισα"),
           "volos": ("τον Βόλο", "Βόλος"), "greece": ("την Ελλάδα", "")}

# KtP 769674-2026: facts read from the RFP pages (§1.3 p17, summary pp10-11). Checked by tests against the page text.
KTP_TENDER = {
    "buyer_gen": "Κοινωνίας της Πληροφορίας Μ.Α.Ε. (ΚτΠ)",
    "title": "Παροχή Υπηρεσιών Συντήρησης, Υποστήριξης και Παραμετροποίησης του Πληροφοριακού Συστήματος Μηχανισμού Πληρωμών Προγραμμάτων Επιδοτήσεων (Escrow Accounts)",
    "adam": "26PROC020137847",
    "esidis": "589064",
    "budget": 200000, "support": 125000, "param_total": 75000, "param_packages": 5, "param_each": 15000,
    "months": 12,
    "deadline": "Δευτέρα 7 Δεκεμβρίου 2026, 14:00",
    "clarifications": "18 Νοεμβρίου 2026",
    "opening": "Παρασκευή 11 Δεκεμβρίου 2026",
}

GAP_EL = {
    "turnover": "συνολικός κύκλος εργασιών 2023–2025 τουλάχιστον 400.000 € (§2.2.5)",
    "profitability": "κερδοφορία σε καθεμία από τις χρήσεις 2023–2025 (§2.2.5)",
    "experience_escrow": "πέντε ολοκληρωμένα έργα συστημάτων πληρωμών μέσω escrow accounts για φορείς του Δημοσίου (§2.2.6.1)",
    "experience_sla": "ένα από αυτά με υποστήριξη βάσει SLA αξίας τουλάχιστον 200.000 € (§2.2.6.1)",
    "experience_transformation": "ένα έργο ψηφιακού μετασχηματισμού διαδικασιών με συντήρηση, για φορέα του Δημοσίου (§2.2.6.1)",
    "iso": "έξι πιστοποιητικά ISO: 9001, 20000-1, 27001, 27701, 22301 και 37001 (§2.2.7)",
}

# profile keywords -> (what we do, in Greek) and (where it fits in THIS tender's work)
CAPABILITIES = [
    (r"web|app|platform|εφαρμογ|πλατφόρμ", "web εφαρμογές", "ανάπτυξη των πακέτων παραμετροποίησης και ένταξης νέων δράσεων στην πλατφόρμα"),
    (r"booking|κρατήσ", "πλατφόρμες κρατήσεων", None),
    (r"dashboard|data|analytics|report|δεδομέν|αναφορ", "πίνακες και αναφορές δεδομένων (dashboards)", "αναφορές και πίνακες για το υποσύστημα πληροφόρησης διοίκησης (MIS) της πλατφόρμας"),
    (r"\bux\b|\bui\b|design|σχεδιασ", "διεπαφές χρηστών", "βελτιώσεις στις διεπαφές των χρηστών"),
    (r"\bsupport|maintenance|υποστήρ|συντήρ", "υποστήριξη και συντήρηση εφαρμογών", "υποστήριξη δεύτερου επιπέδου στο πλαίσιο του SLA"),
]
SECTORS = [(r"touris|τουρισ", "του τουρισμού"), (r"retail|λιαν", "του λιανεμπορίου"), (r"health|υγε", "της υγείας"), (r"public|δημόσι|municipal|δήμ", "του Δημοσίου")]


def _gr_date(d: datetime) -> str:
    return f"{d.day} {GR_MONTHS[d.month - 1]} {d.year}"


def _eur(v: float) -> str:
    return f"{v:,.0f} €".replace(",", ".")


def _city(profile: dict) -> tuple[str, str]:
    loc = (profile.get("location") or "").lower()
    for k, v in CITY_EL.items():
        if k in loc:
            return v
    return "", ""


def _verified_guarantee(run_id: str) -> float | None:
    for r in R.list_receipts(run_id):
        if r["intent"].get("claim_id") == "participation_guarantee" and r["independent_check"]:
            return (r["independent_check"].get("observed") or {}).get("participation_guarantee_eur")
    return None


def _capabilities(profile: dict) -> tuple[list[str], list[str], list[str]]:
    text = f"{profile.get('summary', '')} {' '.join(profile.get('cpv_codes') or [])}".lower()
    what, fits = [], []
    for pat, w, f in CAPABILITIES:
        if re.search(pat, text):
            what.append(w)
            if f:
                fits.append(f)
    sectors = [s for pat, s in SECTORS if re.search(pat, text)]
    if not what:
        what = ["ανάπτυξη λογισμικού"]
    if not fits:
        fits = ["ανάπτυξη των πακέτων παραμετροποίησης και ένταξης νέων δράσεων στην πλατφόρμα"]
    return what, fits, sectors


def _join_el(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " και " + items[-1]


def _projects_line(profile: dict, eligibility: dict) -> str:
    rules = {r["id"]: r for r in eligibility.get("rules", [])}
    p = profile.get("public_sector_projects_last_5y")
    if p is None:
        return ""
    none = re.fullmatch(r"\s*(none|no|κανένα|-)\s*\.?\s*", str(p), re.I)
    esc = rules.get("experience_escrow", {}).get("status")
    if none:
        return "Δεν έχουμε μέχρι σήμερα υλοποιήσει έργα για φορείς του Δημοσίου."
    if esc == "missing":
        return "Έχουμε υλοποιήσει μικρότερα έργα για φορείς του Δημοσίου, όχι όμως συστήματα πληρωμών μέσω escrow accounts."
    return "Έχουμε εμπειρία σε έργα για φορείς του Δημοσίου."


def render_markdown(profile: dict, eligibility: dict, guarantee: float | None) -> str:
    T = KTP_TENDER
    today = config.now_athens()
    name = profile.get("name") or "Η εταιρεία μας"
    size = profile.get("size")
    city, city_nom = _city(profile)
    what, fits, sectors = _capabilities(profile)
    alone = eligibility.get("verdict") == "not_eligible"
    gaps = [GAP_EL[r["id"]] for r in eligibility.get("rules", []) if r["status"] == "missing" and r["id"] in GAP_EL]
    certs = [c for c in (profile.get("certificates") or []) if re.search(r"iso", c, re.I)]

    who = f"Η {name} είναι εταιρεία ανάπτυξης λογισμικού" + (f" {size} ατόμων" if size else "") + (f" με έδρα {city}" if city else "") + "."
    does = f"Αναπτύσσουμε {_join_el(what)}" + (f", κυρίως για επιχειρήσεις {_join_el(sectors)}" if sectors else "") + "."
    gap_lines = "\n".join(f"- {g}" for g in gaps)
    fit_lines = "\n".join(f"- {f}" for f in fits)
    cert_line = f"Διαθέτουμε πιστοποίηση {_join_el(certs)}." if certs else ""
    proj_line = _projects_line(profile, eligibility)
    g_line = (f"Η εγγύηση συμμετοχής ανέρχεται σε {_eur(guarantee)} (2% επί του προϋπολογισμού χωρίς ΦΠΑ και δικαίωμα προαίρεσης, §2.2.2.1) "
              f"και, εκτός αν εκδοθεί ηλεκτρονικά, το πρωτότυπο πρέπει να έχει κατατεθεί στην ΚτΠ πριν από την αποσφράγιση, την {T['opening']}.") if guarantee else ""

    if alone:
        ask = (
            "## Η πρότασή μας\n\n"
            "Αναζητούμε εταίρο που καλύπτει τα κριτήρια εμπειρίας και πιστοποίησης και θα υποβάλει την προσφορά ως ανάδοχος. "
            "Προτείνουμε να συμμετάσχουμε ως υπεργολάβος, χωρίς ο προσφέρων να στηρίζεται στις ικανότητές μας: σε αυτή την περίπτωση "
            "η διακήρυξη ζητά υπεύθυνη δήλωση του προσφέροντος για το τμήμα που ανατίθεται και υπεύθυνη δήλωση αποδοχής από εμάς (§2.2.9.2 Β.10). "
            "Εναλλακτικά εξετάζουμε ένωση οικονομικών φορέων· σημειώνουμε ότι σε ένωση τα πιστοποιητικά της §2.2.7 καλύπτονται από κάθε μέλος χωριστά."
        )
    else:
        ask = "## Η πρότασή μας\n\nΠροτείνουμε κοινή υποβολή προσφοράς ως ένωση οικονομικών φορέων."

    return f"""# Πρόταση συνεργασίας για τον διαγωνισμό της ΚτΠ (ΑΔΑΜ {T['adam']})

**{city_nom + ', ' if city_nom else ''}{_gr_date(today)}**

**Προς:** [Επωνυμία εταίρου], υπόψη [Ονοματεπώνυμο]
**Από:** {name}
**Θέμα:** Συνεργασία στον διαγωνισμό «{T['title']}» της {T['buyer_gen']}, ΕΣΗΔΗΣ α/α {T['esidis']}

Αξιότιμε/η κύριε/κυρία,

{who} {does}

Η ΚτΠ αναζητά ανάδοχο για τη συντήρηση, υποστήριξη και παραμετροποίηση του πληροφοριακού συστήματος πληρωμών μέσω escrow accounts, για {T['months']} μήνες. Ο προϋπολογισμός είναι {_eur(T['budget'])} πλέον ΦΠΑ: {_eur(T['support'])} για υποστήριξη και συντήρηση και {_eur(T['param_total'])} για {T['param_packages']} πακέτα παραμετροποίησης των {_eur(T['param_each'])}, τα οποία παρέχονται κατόπιν αιτήματος. Οι προσφορές υποβάλλονται στο ΕΣΗΔΗΣ έως τη {T['deadline']}.

{"Μελετήσαμε τη διακήρυξη και **δεν μπορούμε να υποβάλουμε προσφορά μόνοι μας**. Δεν καλύπτουμε σήμερα:" if alone and gaps else "Μελετήσαμε τη διακήρυξη."}

{gap_lines}

## Τι μπορούμε να αναλάβουμε στο έργο

{fit_lines}

{" ".join(x for x in (cert_line, proj_line) if x)}

{ask}

{g_line}

Η προθεσμία για αιτήματα διευκρινίσεων λήγει στις {T['clarifications']}. Θα χαρούμε να το συζητήσουμε σε μια σύντομη συνάντηση πριν από τότε.

Με εκτίμηση,

[Ονοματεπώνυμο νόμιμου εκπροσώπου]
{name}

---
*Σχέδιο επιστολής από το Bid-Ready. Ελέγξτε το και υπογράψτε το εσείς. Δεν υποβάλλεται στο ΕΣΗΔΗΣ.*
"""


# ---- fact check for an LLM rewrite ------------------------------------------------------------

ALLOWED_LATIN = {"escrow", "accounts", "iso", "iec", "sla", "mis", "web", "dashboards", "ted", "bid-ready", "it", "ui", "ux", "api", "gdpr"}


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[.,]", "", n) for n in re.findall(r"\d[\d.,]*\d|\d", text)}


def fact_check(candidate: str, draft: str, profile: dict) -> tuple[bool, dict]:
    allowed_nums = _numbers(draft) | _numbers(json.dumps(profile, ensure_ascii=False))
    new_nums = sorted(_numbers(candidate) - allowed_nums)
    allowed_words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]+", draft + " " + (profile.get("name") or ""))} | ALLOWED_LATIN
    latin = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]+", candidate) if w.lower() not in allowed_words]
    ok = not new_nums and len(latin) <= 2 and "ΕΣΗΔΗΣ" in candidate
    return ok, {"new_numbers": new_nums, "unexpected_latin_words": latin[:10], "has_esidis": "ΕΣΗΔΗΣ" in candidate}


POLISH_PROMPT = (
    "Ξαναγράψε την παρακάτω επιστολή σε φυσικά, επαγγελματικά ελληνικά, πιο ζεστά και πιο πειστικά, για τον συγκεκριμένο διαγωνισμό. "
    "Κανόνες: ΜΗΝ προσθέσεις αριθμούς, ποσά, ημερομηνίες, ενότητες ή γεγονότα που δεν υπάρχουν στο κείμενο. Κράτα όλα τα ποσά, τις ημερομηνίες "
    "και τις παραπομπές (§) όπως είναι. Κράτα τη μορφή Markdown, τις αγκύλες [ ] και την τελευταία γραμμή. Όλο το κείμενο στα ελληνικά, "
    "εκτός από τα ονόματα, ISO, SLA, MIS και escrow accounts. Αν το προφίλ περιέχει αγγλικό κείμενο, απόδωσέ το στα ελληνικά χωρίς να προσθέσεις στοιχεία.\n\n"
)


def _polish(draft: str, profile: dict) -> tuple[str | None, str]:
    from . import gemini

    ok, why = gemini.configured()
    if not ok:
        return None, why
    try:
        from google.genai import types

        resp = gemini.client().models.generate_content(
            model=gemini.MODEL,
            contents=POLISH_PROMPT + "ΠΡΟΦΙΛ:\n" + json.dumps({k: profile.get(k) for k in ("name", "summary", "public_sector_projects_last_5y")}, ensure_ascii=False)
                     + "\n\nΕΠΙΣΤΟΛΗ:\n" + draft,
            config=types.GenerateContentConfig(temperature=0.3),
        )
        text = (resp.text or "").strip()
        text = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", text)
        return (text or None), ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _gemini_model() -> str:
    from . import gemini

    return gemini.MODEL


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


def draft_cover_letter(notice_id: str, profile: dict, eligibility: dict, run_id: str | None = None, polish: bool = True) -> dict:
    run_id = run_id or eligibility.get("run_id") or new_run_id()
    d = config.OUT_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    draft = render_markdown(profile, eligibility, _verified_guarantee(run_id))
    md, source, check = draft, "template", None

    if polish:
        candidate, err = _polish(draft, profile)
        if candidate:
            ok, check = fact_check(candidate, draft, profile)
            write_receipt({
                "run_id": run_id, "idempotency_key": f"verify:{run_id}:letter_facts:v1", "actor": "gemini",
                "action": "draft_cover_letter",
                "intent": {"claim_id": "letter_facts", "claim": "The polished letter adds no numbers, dates or English prose beyond the checked draft."},
                "tool_call": {"name": "gemini_polish", "arguments": {"model": _gemini_model()}},
                "tool_response": {"chars": len(candidate)},
                "independent_check": {"checker": "verifier-core", "method": "compare_to_checked_draft", "source": "template draft + profile",
                                      "observed": check, "mismatch": not ok},
                "status": "VERIFIED" if ok else "FAILED",
                "reason": None if ok else "Rewrite rejected; the checked draft is used instead.",
            })
            if ok:
                md, source = candidate, "gemini_polished"
        elif err:
            check = {"skipped": err}

    md_path = d / "consortium_letter_el.md"
    md_path.write_text(md, encoding="utf-8")
    docx_path = d / "consortium_letter_el.docx"
    has_docx = _write_docx(md, docx_path)
    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"draft_cover_letter:{run_id}:{notice_id}",
        "action": "draft_cover_letter",
        "intent": {"notice_id": notice_id, "framing": "consortium_outreach" if eligibility.get("verdict") == "not_eligible" else "cover"},
        "tool_call": {"name": "draft_cover_letter", "arguments": {"notice_id": notice_id, "polish": polish}},
        "tool_response": {"path": str(md_path), "docx": str(docx_path) if has_docx else None, "language": "el", "source": source, "fact_check": check},
        "status": "RECORDED",
        "reason": "Letter file written; existence is re-read by the verifier in build_pack.",
    })
    return {"run_id": run_id, "path": str(md_path), "docx_path": str(docx_path) if has_docx else None, "language": "el",
            "source": source, "fact_check": check, "markdown": md, "receipt": receipt}
