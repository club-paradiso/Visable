#!/usr/bin/env python3
"""All-status AI safety sweep for Paradiso.

Goal
----
Ensure *every* visa/status record returned by ``/api/visas`` (or, locally, by
``visa_data.json``) can pass through the AI context/routing layer without
unsafe metadata behaviour. This is a structural safety sweep, not a proof that
every answer is legally complete.

For each status this sweep builds generic Korean + English prompts and checks
the backend's deterministic helper functions (no LLM provider is called):

  - A generic question must NOT force scenario-specific procedure variants.
  - A generic question must NOT select deterministic manual grounding.
  - ``procedure_variant_context_sources`` may only contain safe metadata
    fields (never raw requiredDocs / manualRefs / full visa_data).
  - Needs-review scenario variants never imply ``grounding_used`` and stay
    separate from source-confirmed grounding.
  - Missing / malformed ``visa_data`` does not crash and fabricates nothing.

For statuses that *do* carry routable variants, a matching task-worded prompt
is additionally probed to confirm variants surface only when the wording
matches — and even then carry ``needs_manual_review`` and never flip grounding.

By default the sweep runs fully locally (imports the backend helpers, loads
``visa_data.json``) so it never needs a live LLM provider. With ``--backend-url``
it additionally exercises ``/api/ask`` over HTTP, accepting the no-provider
HTTP 503 metadata pattern.

Usage:
    python3 scripts/smoke_ai_all_status_safeguards.py
    python3 scripts/smoke_ai_all_status_safeguards.py --limit 10
    python3 scripts/smoke_ai_all_status_safeguards.py --json
    BACKEND_URL=http://127.0.0.1:8000 \
        python3 scripts/smoke_ai_all_status_safeguards.py --backend-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
VISA_DATA = REPO_ROOT / "visa_data.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Routable procedure keys and the wording that should route to each.
ROUTABLE_KEYS = ("statusChange", "workplaceChange", "activitiesOutsideStatus", "statusGrant")
MATCHING_PROMPT = {
    "statusChange": "{code} 체류자격 변경 서류 알려줘",
    "workplaceChange": "{code} 근무처 변경 서류 알려줘",
    "activitiesOutsideStatus": "{code} 체류자격외활동허가 서류 알려줘",
    "statusGrant": "{code} 국내출생 자녀 체류자격 부여 서류 알려줘",
}

# Generic, status-agnostic prompts that must NOT force scenario variants.
GENERIC_KO = "{code} 체류 관련해서 필요한 절차와 주의사항 알려줘"
GENERIC_EN = "What should I watch out for with {code} status in Korea?"

# The only field names allowed in procedure_variant_context_sources.
SAFE_VARIANT_FIELDS = {
    "visa_code", "procedure_key", "variant_id", "label", "status_code",
    "page_range", "manual_name", "manual_version", "needs_manual_review",
}
# Raw fields that must never appear in safe variant metadata.
FORBIDDEN_VARIANT_FIELDS = {"requiredDocs", "manualRefs", "documents", "raw", "visa_data", "notes"}


def _load_backend():
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)
    import paradiso_backend as mod  # noqa: WPS433 — late import after sys.path setup

    mod._reset_visas_cache_for_tests()
    mod._reset_grounding_cache_for_tests()
    return mod


def _load_statuses(backend_url: Optional[str]) -> List[Dict[str, Any]]:
    if backend_url:
        req = urllib.request.Request(
            f"{backend_url.rstrip('/')}/api/visas", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode())
        if isinstance(raw, dict):
            return raw.get("data") or raw.get("visas") or []
        if isinstance(raw, list):
            return raw
        return []
    return json.loads(VISA_DATA.read_text(encoding="utf-8"))


def _routable_variant_keys(record: Dict[str, Any]) -> List[str]:
    procedures = record.get("procedures")
    if not isinstance(procedures, dict):
        return []
    keys: List[str] = []
    for key in ROUTABLE_KEYS:
        proc = procedures.get(key)
        if isinstance(proc, dict) and isinstance(proc.get("variants"), list) and proc.get("variants"):
            keys.append(key)
    return keys


def _check_variant_sources_shape(sources: List[Dict[str, Any]]) -> List[str]:
    """Return list of safety violations found in variant source metadata."""
    problems: List[str] = []
    for src in sources:
        if not isinstance(src, dict):
            problems.append("non-dict source entry")
            continue
        leaked = (set(src.keys()) & FORBIDDEN_VARIANT_FIELDS) | (set(src.keys()) - SAFE_VARIANT_FIELDS)
        if leaked:
            problems.append(f"unexpected/forbidden fields: {sorted(leaked)}")
    return problems


def _sweep_status(mod, record: Dict[str, Any]) -> Dict[str, Any]:
    """Run all deterministic safety checks for a single status record."""
    code = record.get("code") or "?"
    failures: List[str] = []
    warnings: List[str] = []

    routable = _routable_variant_keys(record)
    has_procedures = isinstance(record.get("procedures"), dict) and bool(record.get("procedures"))

    # --- 1. Generic prompts (KO + EN) must not force variants or grounding. ---
    for prompt in (GENERIC_KO.format(code=code), GENERIC_EN.format(code=code)):
        top, sub = mod._detect_visa_codes(code, record, prompt)
        task = mod._detect_task_type(prompt)
        grounding = mod._select_grounding(top, task, sub)
        pv_sources = mod._procedure_variant_context_sources(record, task, sub, user_text=prompt)
        pv_block = mod._build_procedure_variant_context_block(record, task, sub, user_text=prompt)

        if grounding is not None:
            failures.append(f"generic prompt selected deterministic grounding (task={task!r})")
        if pv_sources:
            failures.append(
                f"generic prompt forced {len(pv_sources)} scenario variant(s) (task={task!r})"
            )
        if pv_block:
            failures.append("generic prompt built a variant context block")
        failures.extend(f"generic variant shape: {p}" for p in _check_variant_sources_shape(pv_sources))

    # --- 2. Missing / malformed visa_data must not crash or fabricate. ---
    for bad_payload in (None, {}, {"code": code, "procedures": "oops"}):
        try:
            top, sub = mod._detect_visa_codes(code, bad_payload, GENERIC_KO.format(code=code))
            task = mod._detect_task_type(GENERIC_KO.format(code=code))
            srcs = mod._procedure_variant_context_sources(bad_payload, task, sub, user_text="generic")
        except Exception as exc:  # noqa: BLE001 — any crash is a failure
            failures.append(f"missing/malformed payload crashed: {exc!r}")
            continue
        if srcs:
            failures.append("missing/malformed payload fabricated variant sources")

    # --- 3. Matching task wording surfaces variants safely (only where they exist). ---
    for key in routable:
        prompt = MATCHING_PROMPT[key].format(code=code)
        top, sub = mod._detect_visa_codes(code, record, prompt)
        task = mod._detect_task_type(prompt)
        grounding = mod._select_grounding(top, task, sub)
        pv_sources = mod._procedure_variant_context_sources(record, task, sub, user_text=prompt)

        if not pv_sources:
            warnings.append(f"{key}: matching wording produced no variant sources")
            continue
        # Variant context must never imply deterministic grounding.
        if grounding is not None:
            failures.append(f"{key}: matching wording also selected deterministic grounding")
        # All surfaced sources must be needs-review and shape-safe.
        if any(s.get("needs_manual_review") is not True for s in pv_sources):
            failures.append(f"{key}: surfaced variant without needs_manual_review=true")
        failures.extend(f"{key} variant shape: {p}" for p in _check_variant_sources_shape(pv_sources))
        # Source-confirmed grounding and needs-review variants stay separate.
        if grounding is not None and pv_sources:
            failures.append(f"{key}: grounding and variant context co-asserted")

    return {
        "code": code,
        "has_procedures": has_procedures,
        "routable_variant_keys": routable,
        "failures": failures,
        "warnings": warnings,
    }


def _probe_backend(backend_url: str, record: Dict[str, Any]) -> List[str]:
    """Optional HTTP probe of /api/ask; accepts 200 and no-provider 503 metadata."""
    code = record.get("code") or "?"
    payload = {
        "question": GENERIC_KO.format(code=code),
        "visa_code": code,
        "visa_data": record,
        "lang": "ko",
        "consent": True,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{backend_url.rstrip('/')}/api/ask",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, body = resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            body = json.loads(exc.read().decode())
        except Exception:  # noqa: BLE001
            body = {}
    if status not in (200, 503):
        return [f"{code}: unexpected HTTP {status}"]
    meta = body.get("detail") if status == 503 and isinstance(body.get("detail"), dict) else body
    if not isinstance(meta, dict):
        return []
    problems: List[str] = []
    if meta.get("procedure_variant_context_sources"):
        problems.append(f"{code}: generic HTTP prompt returned variant sources")
    if meta.get("grounding_used") is True and not (meta.get("grounding_sources") or []):
        problems.append(f"{code}: grounding_used=true with empty grounding_sources")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description="All-status AI safety sweep (no live LLM provider required)."
    )
    parser.add_argument("--backend-url", default=os.environ.get("BACKEND_URL"),
                        help="If set, also probe /api/ask over HTTP (accepts no-provider 503).")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of statuses swept.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit a JSON report.")
    args = parser.parse_args()

    mod = _load_backend()
    statuses = _load_statuses(args.backend_url)
    if args.limit is not None:
        statuses = statuses[: args.limit]

    results: List[Dict[str, Any]] = []
    http_problems: List[str] = []
    for record in statuses:
        if not isinstance(record, dict):
            continue
        results.append(_sweep_status(mod, record))
        if args.backend_url:
            http_problems.extend(_probe_backend(args.backend_url, record))

    total = len(results)
    with_procedures = sum(1 for r in results if r["has_procedures"])
    with_variants = sum(1 for r in results if r["routable_variant_keys"])
    no_procedures = sum(1 for r in results if not r["has_procedures"])
    failing = [r for r in results if r["failures"]]
    warning_rows = [r for r in results if r["warnings"]]
    total_failures = sum(len(r["failures"]) for r in failing) + len(http_problems)

    if args.as_json:
        print(json.dumps({
            "total": total,
            "with_parent_procedures": with_procedures,
            "with_variants": with_variants,
            "no_structured_procedures": no_procedures,
            "failures": total_failures,
            "http_problems": http_problems,
            "results": results,
        }, ensure_ascii=False, indent=2))
        return 1 if total_failures else 0

    print(f"All-status AI safety sweep — source: {args.backend_url or VISA_DATA.name}")
    print(f"  total statuses checked      : {total}")
    print(f"  with parent-level procedures: {with_procedures}")
    print(f"  with routable variants      : {with_variants}")
    print(f"  no structured procedures    : {no_procedures}")
    print()

    for r in results:
        tag = "FAIL" if r["failures"] else ("WARN" if r["warnings"] else "OK")
        if tag == "OK":
            continue
        print(f"  {tag:4} {r['code']}")
        for f in r["failures"]:
            print(f"        ! {f}")
        for w in r["warnings"]:
            print(f"        ~ {w}")
    if http_problems:
        print("  HTTP probe problems:")
        for p in http_problems:
            print(f"        ! {p}")

    print()
    print(
        f"Result: {total - len(failing)} OK, {len(warning_rows)} with warnings, "
        f"{len(failing)} with failures  /  {total} statuses  "
        f"({total_failures} total failure(s))"
    )
    return 1 if total_failures else 0


if __name__ == "__main__":
    sys.exit(main())
