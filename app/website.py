"""Onboard from a company website (Firecrawl), with the same discipline as tender rules:
every fact taken from the site keeps an exact quote and the page it came from, and the code checks
the quote is really on that page. Facts the site doesn't state are asked (turnover always is).

Firecrawl API v2: POST https://api.firecrawl.dev/v2/scrape (and /v2/map), Authorization: Bearer <key>.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from . import config
from . import tender_source as T

BASE = "https://api.firecrawl.dev/v2"
PAGE_HINTS = r"about|team|people|services|what-we-do|work|projects|clients|case|quality|iso|certif|σχετικ|ομαδ|υπηρεσ|εργα|πελατ"
MAX_EXTRA_PAGES = 3


class NotConfigured(RuntimeError):
    pass


def configured() -> tuple[bool, str]:
    if config.offline():
        return False, "offline mode (BIDREADY_OFFLINE=1)"
    if not os.environ.get("FIRECRAWL_API_KEY"):
        return False, "FIRECRAWL_API_KEY is not set in .env"
    return True, ""


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}", "Content-Type": "application/json"}


def scrape(url: str, timeout: float = 60) -> dict:
    with httpx.Client(timeout=timeout) as c:
        r = c.post(f"{BASE}/scrape", headers=_headers(), json={"url": url, "formats": ["markdown"], "onlyMainContent": True})
        r.raise_for_status()
        d = (r.json() or {}).get("data") or {}
    meta = d.get("metadata") or {}
    return {"url": meta.get("url") or meta.get("sourceURL") or url, "title": meta.get("title"), "markdown": d.get("markdown") or ""}


def site_links(url: str, timeout: float = 30) -> list[str]:
    """Best effort: other pages on the same site worth reading (about, team, services, projects…)."""
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.post(f"{BASE}/map", headers=_headers(), json={"url": url, "limit": 50})
            r.raise_for_status()
            d = r.json() or {}
    except Exception:
        return []
    raw = d.get("links") or (d.get("data") or {}).get("links") or []
    links = [x.get("url") if isinstance(x, dict) else x for x in raw]
    host = urlparse(url).netloc
    keep = [u for u in links if u and urlparse(u).netloc == host and u.rstrip("/") != url.rstrip("/") and re.search(PAGE_HINTS, u.lower())]
    return list(dict.fromkeys(keep))[:MAX_EXTRA_PAGES]


def read_site(url: str) -> dict:
    """Scrape the page and up to 3 relevant sub-pages. Cached per URL under out/sites/."""
    ok, why = configured()
    if not ok:
        raise NotConfigured(why)
    key = hashlib.sha1(url.strip().encode()).hexdigest()[:12]
    cache = config.OUT_DIR / "sites" / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    pages = [scrape(url)]
    for u in site_links(url):
        try:
            pages.append(scrape(u))
        except Exception:
            continue
    out = {"url": url, "pages": [p for p in pages if p["markdown"].strip()]}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


# ---- extraction (Gemini) + quote check (code) ----------------------------------------------------

_F = {"type": "object", "properties": {"value": {"type": ["string", "null"]}, "quote": {"type": ["string", "null"]},
                                        "page": {"type": ["integer", "null"], "description": "Page number from the ---PAGE n--- marker."}},
      "required": ["value", "quote", "page"]}
_L = {"type": "array", "items": _F}
SCHEMA = {"type": "object", "properties": {
    "name": _F, "team_size": _F, "city": _F, "summary": {"type": ["string", "null"], "description": "One sentence in the site's own words."},
    "services": _L, "certificates": _L, "public_sector_projects": _L},
    "required": ["name", "team_size", "city", "summary", "services", "certificates", "public_sector_projects"]}
SYSTEM = ("You read a company's website for a public-tender tool. Extract only what the pages state; use null or an empty list "
          "otherwise. For every value copy an exact short quote from one page and give that page's number. Public-sector "
          "projects are work for public bodies (ministries, municipalities, public organisations) only.")


def extract(site: dict, reader=None) -> dict:
    ctx = "\n".join(f"---PAGE {i + 1}--- {p['url']}\n{p['markdown'][:15000]}" for i, p in enumerate(site["pages"]))
    if reader is None:
        from google.genai import types

        from . import gemini

        r = gemini.client().models.generate_content(
            model=gemini.MODEL, contents=ctx,
            config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0, response_mime_type="application/json",
                                               response_json_schema=SCHEMA, thinking_config=gemini.fast_thinking()))
        try:
            return json.loads(r.text or "{}")
        except json.JSONDecodeError:
            return {}
    return reader(ctx)


def _checked(item: Any, pages: list[dict]) -> dict | None:
    """Keep a fact only if its quote is on the page it names; attach that page's URL."""
    if not isinstance(item, dict) or not item.get("value") or not item.get("quote"):
        return None
    i = item.get("page")
    if not isinstance(i, int) or not 1 <= i <= len(pages):
        return None
    if T.norm(item["quote"]) not in T.norm(pages[i - 1]["markdown"]):
        return None
    return {"value": str(item["value"]).strip(), "quote": item["quote"], "url": pages[i - 1]["url"]}


def facts(site: dict, reader=None) -> dict:
    cache = config.OUT_DIR / "sites" / f"{hashlib.sha1(site['url'].strip().encode()).hexdigest()[:12]}.facts.json"
    if reader is None and cache.exists():
        raw = json.loads(cache.read_text(encoding="utf-8"))
    else:
        raw = extract(site, reader) or {}
        if reader is None and raw:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    pages = site["pages"]
    out: dict[str, Any] = {"summary": raw.get("summary")}
    dropped = 0
    for k in ("name", "team_size", "city"):
        f = _checked(raw.get(k), pages)
        dropped += bool(raw.get(k) and raw[k].get("value") and not f) if isinstance(raw.get(k), dict) else 0
        out[k] = f
    for k in ("services", "certificates", "public_sector_projects"):
        items = [_checked(x, pages) for x in raw.get(k) or []]
        dropped += sum(1 for x in items if x is None)
        out[k] = [x for x in items if x]
    out["dropped"] = dropped  # values whose quote couldn't be found on the page: not used
    return out
