#!/usr/bin/env python3
"""Build-time official-terms sync for the i18n glossary.

Looks up official English statute titles on the Korean Law Open API
(law.go.kr DRF) for the terms allowlisted in
data/i18n/official-terms.allowlist.json, and writes results to a generated
cache (data/i18n/official-terms.cache.json) plus a human-readable report
(reports/official-terms-sync/sync_report.md).

Policy:
- Credentials come from environment variables only (LAW_OPEN_API_OC, with
  LAW_API_OC accepted as a legacy alias; DATA_GO_KR_API_KEY reserved for
  future data.go.kr sources). They are never required for the app to run and
  must never appear in frontend code.
- Without credentials the script warns, leaves the glossary and cache
  untouched, and exits 0 — safe in CI and offline environments.
- Curated entries in data/i18n/official-terms.json are never overwritten.
  When an API result disagrees with a curated value it is reported as a
  conflict for manual review.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_PATH = REPO_ROOT / "data/i18n/official-terms.json"
ALLOWLIST_PATH = REPO_ROOT / "data/i18n/official-terms.allowlist.json"
CACHE_PATH = REPO_ROOT / "data/i18n/official-terms.cache.json"
REPORT_PATH = REPO_ROOT / "reports/official-terms-sync/sync_report.md"

# Same DRF endpoints used by scripts/probe_korean_law_open_api_2026_05.py
# (HTTP first: HTTPS to law.go.kr DRF is reset in some sandboxes).
SEARCH_ENDPOINTS = [
    "http://www.law.go.kr/DRF/lawSearch.do",
    "https://www.law.go.kr/DRF/lawSearch.do",
]

OC_ENV_CANDIDATES = ["LAW_OPEN_API_OC", "LAW_API_OC"]


def get_oc() -> str | None:
    for key in OC_ENV_CANDIDATES:
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_law_search(oc: str, query: str, target: str) -> dict | None:
    params = urllib.parse.urlencode(
        {"OC": oc, "target": target, "type": "JSON", "query": query, "display": 5}
    )
    last_error: Exception | None = None
    for endpoint in SEARCH_ENDPOINTS:
        url = f"{endpoint}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=20) as res:
                body = res.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except Exception as err:  # noqa: BLE001 — network/parse failures are reported, not fatal
            last_error = err
    print(f"  WARN: lookup failed for {query!r} (target={target}): {last_error}")
    return None


def extract_english_title(payload: dict | None) -> str | None:
    """Pull the first English statute title out of an elaw search response."""
    if not isinstance(payload, dict):
        return None
    body = payload.get("LawSearch") or payload
    laws = body.get("law") if isinstance(body, dict) else None
    if isinstance(laws, dict):
        laws = [laws]
    if not isinstance(laws, list):
        return None
    for law in laws:
        if not isinstance(law, dict):
            continue
        for key in ("법령명영문", "lawNameEng", "영문법령명", "법령명한글"):
            value = law.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def main() -> int:
    glossary = load_json(GLOSSARY_PATH)
    allowlist = load_json(ALLOWLIST_PATH)
    terms = glossary.get("terms", {})
    laws = allowlist.get("laws", [])

    oc = get_oc()
    if not oc:
        print(
            "WARN: no LAW_OPEN_API_OC (or LAW_API_OC) in the environment.\n"
            "      Skipping network sync; the curated glossary and existing cache are kept as-is.\n"
            "      This is safe — the app never needs credentials at runtime."
        )
        return 0

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    previous_cache = {}
    if CACHE_PATH.exists():
        try:
            previous_cache = load_json(CACHE_PATH).get("results", {})
        except (json.JSONDecodeError, OSError):
            previous_cache = {}

    results: dict[str, dict] = {}
    added, changed, unresolved, conflicting = [], [], [], []

    for law in laws:
        term_id = law.get("termId")
        ko_name = law.get("ko")
        if not term_id or not ko_name:
            continue
        print(f"sync: {term_id} ({ko_name})")
        payload = fetch_law_search(oc, ko_name, target="elaw")
        english = extract_english_title(payload)
        entry = {
            "ko": ko_name,
            "en": english,
            "sourceType": "english-law",
            "fetchedAt": generated_at,
        }
        results[term_id] = entry
        if english is None:
            unresolved.append(term_id)
            continue
        prev = previous_cache.get(term_id, {}).get("en")
        if prev is None:
            added.append(term_id)
        elif prev != english:
            changed.append(term_id)
        curated_en = (terms.get(term_id) or {}).get("en")
        if curated_en and curated_en.strip().lower() != english.strip().lower():
            conflicting.append((term_id, curated_en, english))

    CACHE_PATH.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "generatedAt": generated_at,
                "source": "law.go.kr DRF lawSearch (target=elaw)",
                "notes": "Generated cache. Curated values in official-terms.json always win; conflicts require manual review.",
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Official terms sync report",
        "",
        f"- Generated: {generated_at}",
        f"- Terms queried: {len(laws)}",
        f"- Added: {', '.join(added) or '—'}",
        f"- Changed: {', '.join(changed) or '—'}",
        f"- Unresolved: {', '.join(unresolved) or '—'}",
        "",
        "## Conflicts (curated vs API — manual review required, curated wins)",
    ]
    if conflicting:
        for term_id, curated_en, api_en in conflicting:
            lines.append(f"- `{term_id}`: curated `{curated_en}` vs API `{api_en}`")
    else:
        lines.append("- none")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"OK: cache → {CACHE_PATH.relative_to(REPO_ROOT)}")
    print(f"OK: report → {REPORT_PATH.relative_to(REPO_ROOT)}")
    if conflicting:
        print(f"NOTE: {len(conflicting)} conflict(s) need manual review (curated values kept).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
