"""find_tenders: TED Search API v3 (POST, no key), with a local fallback marked UNVERIFIED."""
from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from . import config
from .receipts import new_run_id, write_receipt

FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
    "place-of-performance",
    "estimated-value-proc",      # procedure-level value (KtP: 300,000 incl. option) -- the "TED headline"
    "estimated-value-cur-proc",
    "estimated-value-lot",       # lot-level value (KtP: 200,000)
    "form-type",
    "notice-type",
    "publication-date",
]

SEARCH_CACHE = "search_el_72_full.json"


def cpv_clause(cpv: str | list[str]) -> str:
    """'72*' -> 'classification-cpv = 72*'; ['72','48'] -> '(classification-cpv = 72* OR classification-cpv = 48*)'."""
    items = [cpv] if isinstance(cpv, str) else list(cpv)
    items = [c if c.endswith("*") else f"{c}*" for c in items if c]
    if len(items) == 1:
        return f"classification-cpv = {items[0]}"
    return "(" + " OR ".join(f"classification-cpv = {c}" for c in items) + ")"


def default_query(place: str = "EL*", cpv: str | list[str] = "72*", deadline_from: str = "20261116") -> str:
    return (
        f"place-of-performance = {place} AND {cpv_clause(cpv)} "
        f"AND form-type = competition AND deadline-receipt-tender-date-lot >= {deadline_from}"
    )


def ted_url(pub: str) -> str:
    return f"https://ted.europa.eu/en/notice/-/detail/{pub}"


def _first(v: Any) -> Any:
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _lang(v: Any, prefs: tuple[str, ...] = ("ell", "eng")) -> str | None:
    if isinstance(v, dict):
        for p in prefs:
            if v.get(p):
                return _first(v[p])
        for val in v.values():
            return _first(val)
    return _first(v)


def _num(v: Any) -> float | None:
    v = _first(v)
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """TED raw notice -> Notice dict used everywhere else."""
    pub = raw.get("publication-number")
    lot_values = [float(x) for x in (raw.get("estimated-value-lot") or []) if x not in (None, "")]
    proc_value = _num(raw.get("estimated-value-proc"))
    date = _first(raw.get("deadline-receipt-tender-date-lot")) or ""
    time = _first(raw.get("deadline-receipt-tender-time-lot")) or ""
    cpvs = list(dict.fromkeys(raw.get("classification-cpv") or []))
    places = list(dict.fromkeys(raw.get("place-of-performance") or []))
    return {
        "publication_number": pub,
        "title": _lang(raw.get("notice-title")),
        "buyer_name": _lang(raw.get("buyer-name")),
        "buyer_country": _first(raw.get("buyer-country")),
        "classification_cpv": cpvs,
        "deadline_date": date[:10] or None,
        "deadline_time": time[:5] or None,
        "deadline_raw": {"date": date, "time": time},
        "place_of_performance": places,
        # The value TED shows at procedure level (may include options). Scoring and the naive
        # extractor use this; eligibility must not.
        "estimated_value": proc_value if proc_value is not None else (sum(lot_values) or None),
        "estimated_value_lot": lot_values,
        "currency": _first(raw.get("estimated-value-cur-proc")) or "EUR",
        "ted_url": ted_url(pub) if pub else None,
    }


def _post(query: str, limit: int) -> dict[str, Any]:
    body = {"query": query, "fields": FIELDS, "limit": limit, "onlyLatestVersions": True}
    with httpx.Client(timeout=config.TED_TIMEOUT_S) as c:
        r = c.post(config.TED_SEARCH_URL, json=body, headers={"Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()


def _cache_path(name: str):
    return config.TED_CACHE_DIR / name


def _write_cache(name: str, data: dict) -> None:
    config.TED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _read_cache(name: str) -> dict | None:
    p = _cache_path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _search(query: str, limit: int, cache_name: str) -> tuple[list[dict], str, str | None, int | None]:
    """Returns (raw notices, source, error, total count). source is 'ted_live' or 'local_cache'."""
    err = None
    if not config.offline():
        try:
            data = _post(query, limit)
            _write_cache(cache_name, data)
            return data.get("notices", []), "ted_live", None, data.get("totalNoticeCount")
        except Exception as e:  # timeout, DNS, 5xx
            err = f"{type(e).__name__}: {e}"
    else:
        err = "offline mode (BIDREADY_OFFLINE=1)"
    cached = _read_cache(cache_name) or {}
    return cached.get("notices", []), "local_cache", err, cached.get("totalNoticeCount")


def find_tenders(
    query: str | None = None,
    place: str = "EL*",
    cpv: str = "72*",
    deadline_from: str = "20261116",
    limit: int = 10,
    run_id: str | None = None,
    include: list[str] | None = None,
    cpv_divisions: list[str] | None = None,
) -> dict[str, Any]:
    """Search TED. `cpv_divisions` (e.g. ['72', '48']) replaces `cpv` with an OR across divisions.
    `include` forces specific publication numbers into the result (e.g. the demo tender)."""
    run_id = run_id or new_run_id()
    divs = sorted({d[:2] for d in cpv_divisions or [] if len(d) >= 2})
    q = query or default_query(place, divs or cpv, deadline_from)
    if query:
        cache_name = _hash_name(q)
    elif divs and divs != ["72"]:
        cache_name = f"search_el_{'_'.join(divs)}.json"
    else:
        cache_name = SEARCH_CACHE
    raw, source, err, total = _search(q, max(limit, 50), cache_name)
    notices = [normalize(n) for n in raw]
    have = {n["publication_number"] for n in notices}
    for pub in include or []:
        if pub not in have:
            got = get_notice(pub, run_id=run_id)["notice"]
            if got:
                notices.append(got)
    notices = notices[:limit] + [n for n in notices[limit:] if n["publication_number"] in (include or [])]

    status = "RECORDED" if source == "ted_live" else "UNVERIFIED"
    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"find_tenders:{run_id}:{_hash(q)}:{limit}",
        "action": "find_tenders",
        "intent": {"query": q},
        "tool_call": {"name": "find_tenders", "arguments": {"query": q, "limit": limit, "include": include}},
        "tool_response": {"count": len(notices), "source": source, "publication_numbers": [n["publication_number"] for n in notices]},
        "independent_check": None if source == "ted_live" else {"checker": "verifier-core", "method": "live_ted_hop", "observed": err, "mismatch": None},
        "status": status,
        "reason": None if source == "ted_live" else f"TED unavailable ({err}); served from local cache. Live hop UNVERIFIED.",
    })
    return {"run_id": run_id, "source": source, "notices": notices, "receipt": receipt,
            "query": q, "divisions": divs or [cpv.rstrip("*")], "total": total, "fetched": len(raw)}


def get_notice(publication_number: str, run_id: str | None = None) -> dict[str, Any]:
    run_id = run_id or new_run_id()
    q = f"publication-number = {publication_number}"
    raw, source, err, _ = _search(q, 5, f"{publication_number}.json")
    notice = normalize(raw[0]) if raw else None
    status = "RECORDED" if source == "ted_live" and notice else "UNVERIFIED"
    receipt = write_receipt({
        "run_id": run_id,
        "idempotency_key": f"get_notice:{run_id}:{publication_number}",
        "action": "find_tenders",
        "intent": {"publication_number": publication_number},
        "tool_call": {"name": "get_notice", "arguments": {"publication_number": publication_number}},
        "tool_response": {"found": bool(notice), "source": source},
        "status": status,
        "reason": None if status == "RECORDED" else f"Live TED hop not confirmed ({err or 'not found'}).",
    })
    return {"run_id": run_id, "source": source, "notice": notice, "receipt": receipt}


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:10]


def _hash_name(q: str) -> str:
    return f"q_{_hash(q)}.json"


if __name__ == "__main__":  # python -m app.ted
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    res = find_tenders(include=["769674-2026"])
    print(f"source={res['source']} receipt={res['receipt']['status']}")
    for n in res["notices"]:
        print(f"{n['publication_number']} | {n['deadline_date']} {n['deadline_time']} | {n['estimated_value']} | {n['classification_cpv']} | {(n['title'] or '')[:70]}")
        print(f"   {n['buyer_name']} -> {n['ted_url']}")
