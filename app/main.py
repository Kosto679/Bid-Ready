"""FastAPI backend + curated one-page UI. Run: uvicorn app.main:app --reload --port 8000"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, config, verifier
from . import receipts as R
from .profile import DEMO_ANSWERS, DEMO_LINES, onboard

app = FastAPI(title="Bid-Ready")
WEB = config.ROOT / "web"


class OnboardIn(BaseModel):
    lines: str = ""
    answers: dict[str, Any] | None = None
    run_id: str | None = None


class MatchesIn(BaseModel):
    profile: dict[str, Any]
    run_id: str | None = None
    value_min: float | None = None
    value_max: float | None = None


class PrepareIn(BaseModel):
    notice_id: str
    profile: dict[str, Any]
    run_id: str | None = None


class PackIn(BaseModel):
    run_id: str
    notice_id: str


@app.get("/health")
def health() -> dict:
    return {"ok": True, "offline": config.offline()}


@app.get("/api/demo")
def demo() -> dict:
    return {"lines": DEMO_LINES, "answers": DEMO_ANSWERS}


@app.post("/api/onboard")
def api_onboard(body: OnboardIn) -> dict:
    return onboard(body.lines, body.answers, run_id=body.run_id)


@app.post("/api/matches")
def api_matches(body: MatchesIn) -> dict:
    return agent.shortlist(body.profile, run_id=body.run_id, value_min=body.value_min, value_max=body.value_max)


@app.post("/api/prepare")
def api_prepare(body: PrepareIn) -> dict:
    res = agent.prepare_bid(body.notice_id, body.profile, run_id=body.run_id)
    res["eligibility"].pop("claims", None)
    return res


@app.get("/api/runs/{run_id}/receipts")
def api_receipts(run_id: str) -> dict:
    return {"receipts": R.list_receipts(run_id), "state": verifier.run_state(run_id)}


@app.post("/api/pack")
def api_pack(body: PackIn) -> dict:
    return agent.handover(body.run_id, body.notice_id)


class EvalIn(BaseModel):
    conditions: list[str] = ["headline", "page"]
    trials: int = 1


@app.get("/api/evals/latest")
def api_eval_latest() -> dict:
    from . import evals, gemini

    ok, why = gemini.configured()
    h = evals.history(2)
    return {"result": h[0] if h else None, "previous": h[1] if len(h) > 1 else None, "configured": ok, "why": why, "model": gemini.MODEL}


@app.post("/api/evals/run")
def api_eval_run(body: EvalIn) -> dict:
    from . import evals, gemini

    conds = tuple(c for c in body.conditions if c in evals.CONDITIONS) or ("headline", "page")
    try:
        prev = evals.latest()
        return {"result": evals.run_eval(conditions=conds, trials=max(1, min(body.trials, 5))), "previous": prev}
    except gemini.NotConfigured as e:
        raise HTTPException(400, f"Gemini is not configured: {e}")


@app.post("/api/rules/agreement")
def api_rules_agreement() -> dict:
    """Run the generic rule reader on ΚτΠ, verify it, and score it against the hand-made index."""
    from datetime import datetime

    from . import gemini
    from . import rules as RL

    ok, why = gemini.configured()
    if not ok:
        raise HTTPException(400, f"Gemini is not configured: {why}")
    r = RL.read("769674-2026")
    run_id = "agree_" + datetime.now(config.ATHENS).strftime("%Y%m%d_%H%M%S")
    receipts = verifier.verify(run_id, r["claims"]) if r["claims"] else []
    return {"agreement": RL.agreement_with_index(r["rules"]), "source": r["source"]["note"],
            "verified": sum(x["status"] == "VERIFIED" for x in receipts), "checks": len(receipts)}


@app.post("/api/live/{notice_id}")
def api_live(notice_id: str) -> dict:
    from . import gemini
    from . import live_extract as LX

    if notice_id not in LX.PACKS:
        raise HTTPException(404)
    try:
        return LX.run(notice_id)
    except gemini.NotConfigured as e:
        raise HTTPException(400, f"Gemini is not configured: {e}")


@app.get("/api/tenders/{notice_id}/rfp")
def api_rfp(notice_id: str) -> FileResponse:
    """The tender's RFP PDF, inline, so links like .../rfp#page=27 open at the cited page."""
    from . import live_extract as LX
    from . import tender_source as T

    if notice_id == "769674-2026":
        p = T.notice_dir(notice_id) / T.rfp_file_rel()
    elif notice_id in LX.PACKS:
        p = config.DATA_DIR / LX.PACKS[notice_id]["pack"] / LX.PACKS[notice_id]["pdf"]
    else:
        raise HTTPException(404)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="application/pdf", filename=f"RFP_{notice_id}.pdf", content_disposition_type="inline")


@app.get("/api/runs/{run_id}/letter")
def api_letter(run_id: str) -> FileResponse:
    p = _safe(run_id) / "consortium_letter_el.md"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="text/markdown; charset=utf-8")


@app.get("/api/runs/{run_id}/zip")
def api_zip(run_id: str) -> FileResponse:
    zips = sorted(_safe(run_id).glob("bidready_pack_*.zip"))
    if not zips:
        raise HTTPException(404)
    return FileResponse(zips[0], filename=zips[0].name, media_type="application/zip")


def _safe(run_id: str) -> Path:
    if not run_id.replace("_", "").isalnum():
        raise HTTPException(400)
    return config.OUT_DIR / run_id


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/web", StaticFiles(directory=WEB), name="web")
