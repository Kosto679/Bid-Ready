"""Eval harness, with stand-in models (no network, no Google credentials)."""
from app import evals, verifier
from app import receipts as R

KTP = "769674-2026"


def oracle(question, context):
    """Answers every field correctly by reading the observer (a perfect model)."""
    f = next(f for f in evals.FIELDS if f["q"] == question)
    o = verifier.OBSERVERS[f["id"]](KTP)
    return {"value": str(o["value"]), "quote": o["quote"]}


def naive(question, context):
    """Trusts the TED headline: guarantee = 2% of 300,000; abstains otherwise."""
    if "participation guarantee" in question:
        return {"value": "6000", "quote": "estimated_value"}
    return {"value": None, "quote": None}


def test_oracle_is_all_correct_on_pages():
    res = evals.run_eval(model_fn=oracle, model_name="oracle", conditions=("page",))
    s = res["summary"]["page"]
    assert s["n"] == len(evals.FIELDS) and s["correct"] == s["n"] and s["accuracy"] == 1.0
    # every quote is verbatim except the ISO count, whose observer quote is a summary list
    assert [r["field"] for r in res["rows"] if not r["grounded"]] == ["iso_certificates_required"]


def test_naive_headline_guarantee_fails_against_page():
    res = evals.run_eval(model_fn=naive, model_name="naive", conditions=("headline",))
    g = next(r for r in res["rows"] if r["field"] == "participation_guarantee_eur")
    assert g["outcome"] == "wrong" and g["observed"] == 4000
    s = res["summary"]["headline"]
    assert s["wrong"] == 1 and s["abstained"] == len(evals.FIELDS) - 1
    # graded by the verifier, receipt points at the page
    rec = next(r for r in R.list_receipts(res["run_id"]) if r["intent"]["claim_id"].endswith("participation_guarantee_eur:1"))
    assert rec["status"] == "FAILED" and "p27" in rec["independent_check"]["source"]


def test_model_errors_are_unverified():
    def broken(q, c):
        raise TimeoutError("vertex timeout")

    res = evals.run_eval(model_fn=broken, model_name="broken", conditions=("page",), fields=["submission_deadline"])
    assert res["rows"][0]["outcome"] == "error" and res["summary"]["page"]["errors"] == 1


def test_parse_answer_formats():
    p = evals.parse_answer
    assert p("4.000,00 €", "num") == 4000.0
    assert p("4,000", "num") == 4000.0
    assert p("€ 200000", "num") == 200000.0
    assert p("12 months", "int") == 12
    assert p("2026-12-07 14:00", "datetime") == "2026-12-07T14:00"
    assert p("07-12-2026, 14:00", "datetime") == "2026-12-07T14:00"
    assert p(None, "num") is None and p("null", "int") is None


def test_latest_and_markdown_saved():
    evals.run_eval(model_fn=naive, model_name="naive", conditions=("headline",), fields=["participation_guarantee_eur"])
    lat = evals.latest()
    assert lat and lat["model"] == "naive"
    assert "| headline | participation_guarantee_eur | 6000.0 | 4000.0 | wrong |" in evals.to_markdown(lat)
