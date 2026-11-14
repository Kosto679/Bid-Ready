"""Eval harness: how well does a model extract tender facts, judged by the deterministic verifier?

For each field x condition the model answers from a given context; the verifier re-reads the
tender page and grades the answer (VERIFIED = correct, FAILED = wrong). Abstaining (null) is
scored separately: on the TED headline it is the right behaviour for most fields.

Conditions
  headline  TED notice metadata only (what a naive pipeline sees; includes the EUR 300,000 value)
  page      the cited PDF page text(s)
  full      the whole RFP text (large context; opt-in)

Run: python -m app.evals --conditions headline,page --trials 1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable

from . import config, ted, verifier
from . import tender_source as T
from .receipts import write_receipt

KTP = "769674-2026"
ModelFn = Callable[[str, str], dict]

NUM = "Answer with a number only, in EUR without separators (e.g. 12500)."
DT = "Answer as YYYY-MM-DDTHH:MM in Europe/Athens local time."
INT = "Answer with an integer only."

FIELDS: list[dict[str, Any]] = [
    {"id": "initial_budget_ex_vat_eur", "q": f"What is the contract's initial estimated value excluding VAT and excluding any option? {NUM}", "pages": [17], "type": "num"},
    {"id": "participation_guarantee_eur", "q": f"What amount must the participation guarantee (εγγύηση συμμετοχής) be? {NUM}", "pages": [27], "type": "num"},
    {"id": "turnover_3y_min_eur", "q": f"What is the minimum TOTAL turnover required across the last three financial years combined? If the text states it as a percentage of the contract budget, calculate the amount using the budget base that the text specifies. {NUM}", "pages": [33, 17], "type": "num"},
    {"id": "performance_guarantee_eur", "q": f"What amount must the performance guarantee (εγγύηση καλής εκτέλεσης) be? If the text states it as a percentage of the contract value, calculate the amount using the value base that the text specifies. {NUM}", "pages": [72, 17], "type": "num"},
    {"id": "submission_deadline", "q": f"When is the deadline for submitting offers? {DT}", "pages": [11], "type": "datetime"},
    {"id": "technical_opening", "q": f"When are the offers opened (αποσφράγιση)? {DT}", "pages": [11], "type": "datetime"},
    {"id": "escrow_projects_required", "q": f"How many completed public-sector escrow-account payment system projects must a bidder have? {INT}", "pages": [33], "type": "int"},
    {"id": "contract_duration_months", "q": f"What is the contract duration in months? {INT}", "pages": [17], "type": "int"},
    {"id": "iso_certificates_required", "q": f"How many different ISO certificates must a bidder hold? {INT}", "pages": [36, 37], "type": "int"},
]

CONDITIONS = ("headline", "page", "full")


# ---- contexts --------------------------------------------------------------------------------

def _headline_context() -> str:
    n = ted.get_notice(KTP, run_id="eval_context")["notice"] or {}
    keep = {k: n.get(k) for k in ("publication_number", "title", "buyer_name", "classification_cpv", "estimated_value",
                                  "currency", "deadline_date", "deadline_time", "place_of_performance")}
    return "TED notice metadata (JSON):\n" + json.dumps(keep, ensure_ascii=False, indent=1)


def _page_context(pages: list[int]) -> str:
    return "\n".join(f"---PDF p{p}---\n{T.page_text(KTP, p)}" for p in pages)


def _full_context() -> str:
    return (T.notice_dir(KTP) / "text" / "rfp_compact.txt").read_text(encoding="utf-8")


def context_for(condition: str, field: dict) -> str:
    if condition == "headline":
        return _headline_context()
    if condition == "page":
        return _page_context(field["pages"])
    if condition == "full":
        return _full_context()
    raise ValueError(condition)


# ---- answer parsing --------------------------------------------------------------------------

def parse_answer(raw: Any, kind: str) -> Any:
    """Normalise a model answer. Returns None for null / unparseable."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("null", "none", "n/a", "unknown"):
        return None
    if kind in ("num", "int"):
        s = s.replace("€", "").replace("EUR", "").replace(" ", "").replace(" ", "")
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):          # Greek 4.000,00
            s = s.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):        # English 4,000.00
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
        m = re.search(r"-?\d+(\.\d+)?", s)
        if not m:
            return None
        v = float(m.group(0))
        return int(v) if kind == "int" else v
    if kind == "datetime":
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}"
        m = re.search(r"(\d{2})[-/.](\d{2})[-/.](\d{4}).*?(\d{2}):(\d{2})", s)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}:{m.group(5)}"
        return None
    return s


def grounded(quote: str | None, context: str) -> bool:
    if not quote:
        return False
    q = T.norm(quote)
    return len(q) >= 6 and q in T.norm(context)


# ---- run -------------------------------------------------------------------------------------

def _default_model() -> tuple[ModelFn, str]:
    from . import gemini

    ok, why = gemini.configured()
    if not ok:
        raise gemini.NotConfigured(why)
    return gemini.ask, gemini.MODEL


def run_eval(model_fn: ModelFn | None = None, model_name: str | None = None,
             conditions: tuple[str, ...] = ("headline", "page"), trials: int = 1,
             fields: list[str] | None = None, progress: Callable[[str], None] | None = None) -> dict:
    if model_fn is None:
        model_fn, model_name = _default_model()
    model_name = model_name or "custom"
    run_id = "eval_" + datetime.now(config.ATHENS).strftime("%Y%m%d_%H%M%S")
    chosen = [f for f in FIELDS if not fields or f["id"] in fields]
    rows: list[dict] = []

    for cond in conditions:
        for f in chosen:
            ctx = context_for(cond, f)
            for trial in range(1, trials + 1):
                claim_id = f"eval:{cond}:{f['id']}:{trial}"
                try:
                    ans = model_fn(f["q"], ctx)
                    err = None
                except Exception as e:  # transport / auth / quota
                    ans, err = {"value": None, "quote": None}, f"{type(e).__name__}: {e}"
                value = parse_answer(ans.get("value"), f["type"])
                row = {"condition": cond, "field": f["id"], "trial": trial, "raw": ans.get("value"), "value": value,
                       "quote": ans.get("quote"), "grounded": grounded(ans.get("quote"), ctx)}
                if err:
                    row.update(outcome="error", status="UNVERIFIED", error=err)
                    write_receipt({"run_id": run_id, "idempotency_key": f"verify:{run_id}:{claim_id}:v1", "actor": model_name,
                                   "action": "eval_extract", "intent": {"claim_id": claim_id, "claim": f["q"]},
                                   "tool_call": {"name": "model", "arguments": {"condition": cond}}, "tool_response": {"error": err},
                                   "status": "UNVERIFIED", "reason": "Model call failed; nothing to verify."})
                elif value is None:
                    row.update(outcome="abstained", status="RECORDED")
                    write_receipt({"run_id": run_id, "idempotency_key": f"verify:{run_id}:{claim_id}:v1", "actor": model_name,
                                   "action": "eval_extract", "intent": {"claim_id": claim_id, "claim": f["q"]},
                                   "tool_call": {"name": "model", "arguments": {"condition": cond}}, "tool_response": {"value": None, "quote": ans.get("quote")},
                                   "status": "RECORDED", "reason": "Model abstained (no value)."})
                else:
                    r = verifier.verify_claim(run_id, {
                        "claim_id": claim_id, "notice_id": KTP, "kind": "field_value", "origin": "eval_extract",
                        "actor": model_name, "statement": f"{f['id']} = {value} ({cond})", "value": value,
                        "check": {"field": f["id"]}, "tool_call": {"name": "model", "arguments": {"condition": cond, "field": f["id"]}},
                        "basis": ans.get("quote"),
                    })
                    row.update(status=r["status"], outcome={"VERIFIED": "correct", "FAILED": "wrong"}.get(r["status"], "error"),
                               observed=(r["independent_check"] or {}).get("observed", {}).get(f["id"]))
                rows.append(row)
                if progress:
                    progress(f"{cond:8} {f['id']:28} -> {row['outcome']}")

    summary = summarize(rows)
    result = {"run_id": run_id, "model": model_name, "notice_id": KTP, "conditions": list(conditions), "trials": trials,
              "ts": datetime.now(config.ATHENS).isoformat(timespec="seconds"), "summary": summary, "rows": rows}
    _save(result)
    return result


def summarize(rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    by = defaultdict(list)
    for r in rows:
        by[r["condition"]].append(r)
    for cond, rs in by.items():
        n = len(rs)
        c = sum(r["outcome"] == "correct" for r in rs)
        w = sum(r["outcome"] == "wrong" for r in rs)
        a = sum(r["outcome"] == "abstained" for r in rs)
        e = sum(r["outcome"] == "error" for r in rs)
        answered = c + w
        out[cond] = {"n": n, "correct": c, "wrong": w, "abstained": a, "errors": e,
                     "accuracy": round(c / n, 3) if n else 0.0,
                     "precision": round(c / answered, 3) if answered else None,
                     "grounded": round(sum(r["grounded"] for r in rs if r["outcome"] in ("correct", "wrong")) / answered, 3) if answered else None}
    return out


def _save(result: dict) -> None:
    d = config.OUT_DIR / "evals"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{result['run_id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / f"{result['run_id']}.md").write_text(to_markdown(result), encoding="utf-8")


def history(n: int = 2) -> list[dict]:
    """The n most recent eval results, newest first."""
    d = config.OUT_DIR / "evals"
    files = sorted(d.glob("eval_*.json")) if d.exists() else []
    return [json.loads(f.read_text(encoding="utf-8")) for f in reversed(files[-n:])]


def latest() -> dict | None:
    h = history(1)
    return h[0] if h else None


def to_markdown(result: dict) -> str:
    lines = [f"# Model eval - {result['model']} on TED {result['notice_id']}", "", f"Run {result['run_id']} at {result['ts']}; graded by verifier re-reading the PDF pages.", "",
             "| Condition | Correct | Wrong | Abstained | Errors | Accuracy | Precision | Grounded quotes |", "|---|---|---|---|---|---|---|---|"]
    for cond, s in result["summary"].items():
        pct = lambda v: "-" if v is None else f"{v:.0%}"
        lines.append(f"| {cond} | {s['correct']} | {s['wrong']} | {s['abstained']} | {s['errors']} | {pct(s['accuracy'])} | {pct(s['precision'])} | {pct(s['grounded'])} |")
    lines += ["", "| Condition | Field | Model said | Page says | Outcome |", "|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append(f"| {r['condition']} | {r['field']} | {r['value'] if r['value'] is not None else '(abstained)'} | {r.get('observed', '')} | {r['outcome']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Run the Bid-Ready model eval on TED 769674-2026.")
    ap.add_argument("--conditions", default="headline,page", help="comma list of: headline,page,full")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--fields", default="", help="comma list of field ids (default: all)")
    ap.add_argument("--model", default=None, help="Gemini model id (default: GEMINI_MODEL or gemini-2.5-flash)")
    a = ap.parse_args(argv)
    from . import gemini

    if a.model:
        gemini.MODEL = a.model
    try:
        res = run_eval(conditions=tuple(c for c in a.conditions.split(",") if c), trials=a.trials,
                       fields=[f for f in a.fields.split(",") if f] or None, progress=print)
    except gemini.NotConfigured as e:
        print(f"Gemini is not configured: {e}. See README 'Model eval'.")
        return 2
    print()
    print(to_markdown(res))
    print(f"Saved out/evals/{res['run_id']}.json and .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
