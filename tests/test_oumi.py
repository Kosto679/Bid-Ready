"""Oumi Iris checks: advisory second opinion on meaning-based rules; sentence claim-check gates the letter rewrite."""
from app import eligibility, letter, oumi
from app import receipts as R
from app import verifier


def test_second_opinion_is_advisory(studio_profile):
    rep = eligibility.check_eligibility("769674-2026", studio_profile, run_id="op1")
    before = (rep["verdict"], verifier.run_state("op1")["state"])
    seen = {}

    def asker(state, qs):
        seen.update(qs)
        return {k: {"type": "noul", "noul": 0.9 if k == "experience_escrow" else 0.1} for k in qs}

    eligibility._second_opinion(rep, studio_profile, asker=asker)
    rows = {r["id"]: r for r in rep["rules"]}
    assert set(seen) >= {"experience_escrow", "team"} and "turnover" not in seen  # numbers are code's job
    assert rows["experience_escrow"]["second_opinion"] == {"p_meets": 0.9, "opinion": "meets", "agrees": False}
    assert rows["team"]["second_opinion"]["agrees"] is True   # we can't tell, Oumi doesn't see it either
    assert (rep["verdict"], verifier.run_state("op1")["state"]) == before
    rec = next(r for r in R.list_receipts("op1") if r["action"] == "second_opinion")
    assert rec["status"] == "RECORDED" and rec["independent_check"]["mismatch"] is True


def test_sentences_skip_headings_and_placeholders():
    md = "# Θέμα\n\n- Η εταιρεία μας αναπτύσσει διαδικτυακές εφαρμογές από το 2019.\n\n[Υπογραφή]\n\nΟΚ."
    assert oumi.sentences(md) == ["Η εταιρεία μας αναπτύσσει διαδικτυακές εφαρμογές από το 2019."]


def test_unsupported_sentence_rejects_rewrite():
    draft = "Είμαστε ομάδα 8 ατόμων στην Αθήνα και αναπτύσσουμε εφαρμογές."
    cand = "Είμαστε ομάδα 8 ατόμων στην Αθήνα και αναπτύσσουμε εφαρμογές. Έχουμε υλοποιήσει δεκάδες έργα για υπουργεία."
    ok, res = letter._claim_check("lc1", cand, draft, asker=lambda st, qs: {"s0": {"noul": 0.95}, "s1": {"noul": 0.05}})
    assert not ok and res["unsupported"][0]["sentence"].startswith("Έχουμε υλοποιήσει")
    rec = next(r for r in R.list_receipts("lc1") if r["intent"].get("claim_id") == "letter_claims")
    assert rec["status"] == "FAILED" and rec["actor"] == "oumi"


def test_not_configured_skips_quietly():
    assert oumi.configured()[0] is False
    assert letter._claim_check("lc2", "x", "y") == (True, None)
