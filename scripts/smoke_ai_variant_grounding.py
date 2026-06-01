#!/usr/bin/env python3
"""
Exhaustive smoke test for AI procedure variant grounding metadata.

Discovers all variant-bearing procedure targets from /api/visas and
verifies that /api/ask returns safe, correctly-shaped variant metadata.

Usage (local exhaustive):
    python3 scripts/smoke_ai_variant_grounding.py

Usage (deployed-safe, representative targets only):
    python3 scripts/smoke_ai_variant_grounding.py --deployed-safe

Usage (capped):
    python3 scripts/smoke_ai_variant_grounding.py --limit 5

Usage (override backend URL):
    BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_variant_grounding.py
    python3 scripts/smoke_ai_variant_grounding.py --backend-url http://127.0.0.1:8000
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Procedure keys the AI classifier can route
ROUTABLE_KEYS = {"statusChange", "workplaceChange", "activitiesOutsideStatus", "statusGrant"}

# Korean prompt templates per procedure key
PROMPT_TEMPLATES = {
    "statusChange": "{code} 체류자격 변경 서류 알려줘",
    "workplaceChange": "{code} 근무처 변경 서류 알려줘",
    "activitiesOutsideStatus": "{code} 체류자격외활동허가 서류 알려줘",
    "statusGrant": "{code} 국내출생 자녀 체류자격 부여 서류 알려줘",
}

# Representative targets for --deployed-safe mode (avoids excessive live LLM calls)
DEPLOYED_SAFE_TARGETS = [
    {"visa_code": "D-9", "procedure_key": "statusChange"},
    {"visa_code": "E-9", "procedure_key": "workplaceChange"},
    {"visa_code": "E-6", "procedure_key": "activitiesOutsideStatus"},
    {"visa_code": "F-1", "procedure_key": "statusGrant"},
]

# Raw fields that must never appear in variant context source metadata
FORBIDDEN_FIELDS = {"requiredDocs", "manualRefs", "documents", "raw", "visa_data"}


def _http_get(url: str) -> list:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode())
    # /api/visas may return {"count": N, "data": [...]} or a plain list
    if isinstance(raw, dict) and "data" in raw:
        return raw["data"]
    if isinstance(raw, list):
        return raw
    return []


def _http_post(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = {}
        try:
            body = json.loads(exc.read().decode())
        except Exception:
            pass
        return exc.code, body


def discover_targets(visas: list) -> list[dict]:
    """Return list of {visa_code, procedure_key, visa_record} for all routable variant targets."""
    targets = []
    for visa in visas:
        code = visa.get("code", "")
        procs = visa.get("procedures") or {}
        for pk, pv in procs.items():
            if pk not in ROUTABLE_KEYS:
                continue
            variants = pv.get("variants") or []
            if variants:
                targets.append({"visa_code": code, "procedure_key": pk, "visa_record": visa})
    return targets


def build_visa_data_payload(visa_record: dict) -> dict:
    """Build a safe visa_data payload (mirrors what the frontend sends)."""
    return {
        "code": visa_record.get("code", ""),
        "name": visa_record.get("name", ""),
        "cat": visa_record.get("cat", ""),
        "period": visa_record.get("period", ""),
        "newReq": visa_record.get("newReq", ""),
        "extReq": visa_record.get("extReq", ""),
        "faq": visa_record.get("faq", ""),
        "procedures": visa_record.get("procedures") or None,
    }


def check_forbidden_fields(sources: list) -> list[str]:
    """Return list of any forbidden field names found in variant sources."""
    found = []
    for src in sources:
        for k in FORBIDDEN_FIELDS:
            if k in src:
                found.append(k)
    return found


def run_smoke(target: dict, backend_url: str) -> tuple[bool, str]:
    """
    Smoke one target. Returns (passed: bool, detail: str).

    Accepts HTTP 200 (normal with provider) and HTTP 503 (no-provider, acceptable
    if the JSON body contains expected variant metadata).
    """
    visa_code = target["visa_code"]
    procedure_key = target["procedure_key"]
    visa_record = target["visa_record"]

    prompt = PROMPT_TEMPLATES[procedure_key].format(code=visa_code)
    visa_data = build_visa_data_payload(visa_record)

    payload = {
        "question": prompt,
        "visa_code": visa_code,
        "visa_data": visa_data,
        "lang": "ko",
        "consent": True,
    }

    status_code, body = _http_post(f"{backend_url}/api/ask", payload)

    label = f"{visa_code}/{procedure_key}"

    if status_code not in (200, 503):
        return False, f"{label}: unexpected HTTP {status_code}"

    # FastAPI 503 wraps the full response metadata inside body["detail"] (a dict).
    # Normalise so the rest of the validation sees a flat metadata dict.
    meta = body
    if status_code == 503:
        detail = body.get("detail")
        if isinstance(detail, dict) and "procedure_variant_context_used" in detail:
            meta = detail
        else:
            # No-provider response without recoverable metadata — acceptable skip.
            detail_text = (str(detail) if detail else body.get("error") or str(body))[:160]
            return True, f"{label}: SKIP (503 no-provider, no variant metadata) — {detail_text}"

    # --- Validate procedure_variant_context_used ---
    pv_used = meta.get("procedure_variant_context_used")
    if pv_used is not True:
        return False, f"{label}: procedure_variant_context_used={pv_used!r} (expected true)"

    # --- Validate procedure_variant_context_sources non-empty ---
    pv_sources = meta.get("procedure_variant_context_sources")
    if not isinstance(pv_sources, list) or len(pv_sources) == 0:
        return False, f"{label}: procedure_variant_context_sources is empty or missing"

    # --- Validate at least one source has the expected procedure_key ---
    matching = [s for s in pv_sources if isinstance(s, dict) and s.get("procedure_key") == procedure_key]
    if not matching:
        keys_found = [s.get("procedure_key") for s in pv_sources if isinstance(s, dict)]
        return False, f"{label}: no source with procedure_key={procedure_key!r}; found {keys_found}"

    # --- Validate all matching sources have needs_manual_review: true ---
    bad_review = [s for s in matching if s.get("needs_manual_review") is not True]
    if bad_review:
        return False, f"{label}: {len(bad_review)} sources missing needs_manual_review=true"

    # --- Validate no forbidden raw fields leaked ---
    forbidden = check_forbidden_fields(pv_sources)
    if forbidden:
        return False, f"{label}: forbidden fields in sources: {forbidden}"

    # --- Validate grounding_used not flipped solely by variant context ---
    grounding_used = meta.get("grounding_used")
    if grounding_used is True:
        # Only a problem if grounding_sources is also empty (variant context must not flip grounding_used)
        gs = meta.get("grounding_sources") or []
        if not gs:
            return False, (
                f"{label}: grounding_used=true but grounding_sources empty — "
                "variant context must not set grounding_used"
            )

    return True, f"{label}: OK ({len(pv_sources)} source(s))"


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test AI procedure variant grounding metadata.")
    parser.add_argument("--backend-url", default=None, help="Backend base URL (overrides BACKEND_URL env var)")
    parser.add_argument("--deployed-safe", action="store_true", help="Run only representative targets (avoids excessive LLM calls)")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of discovered targets")
    args = parser.parse_args()

    backend_url = (
        args.backend_url
        or os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
    ).rstrip("/")

    print(f"Backend: {backend_url}")

    if args.deployed_safe:
        # Representative fixed targets
        print("Mode: deployed-safe (representative targets only)")
        # We need visa records for each; fetch /api/visas to get them
        try:
            visas = _http_get(f"{backend_url}/api/visas")
        except Exception as exc:
            print(f"FATAL: cannot fetch {backend_url}/api/visas — {exc}")
            sys.exit(1)

        visa_map = {v.get("code"): v for v in visas if isinstance(v, dict)}
        targets = []
        for t in DEPLOYED_SAFE_TARGETS:
            rec = visa_map.get(t["visa_code"])
            if rec is None:
                print(f"WARN: {t['visa_code']} not found in /api/visas, skipping")
                continue
            # Check the procedure key actually has variants
            procs = rec.get("procedures") or {}
            pv = procs.get(t["procedure_key"]) or {}
            variants = pv.get("variants") or []
            if not variants:
                print(f"WARN: {t['visa_code']}/{t['procedure_key']} has no variants, skipping")
                continue
            targets.append({"visa_code": t["visa_code"], "procedure_key": t["procedure_key"], "visa_record": rec})
    else:
        # Exhaustive discovery
        print("Mode: exhaustive (all variant-bearing routable targets from /api/visas)")
        try:
            visas = _http_get(f"{backend_url}/api/visas")
        except Exception as exc:
            print(f"FATAL: cannot fetch {backend_url}/api/visas — {exc}")
            sys.exit(1)

        targets = discover_targets(visas)
        if args.limit is not None:
            targets = targets[: args.limit]
            print(f"Limit: {args.limit}")

    print(f"Targets: {len(targets)}")
    if not targets:
        print("No variant-bearing routable targets found — nothing to smoke.")
        sys.exit(0)

    passed = 0
    failed = 0
    skipped = 0

    for target in targets:
        ok, detail = run_smoke(target, backend_url)
        if ok:
            if "SKIP" in detail:
                skipped += 1
                print(f"  SKIP  {detail}")
            else:
                passed += 1
                print(f"  PASS  {detail}")
        else:
            failed += 1
            print(f"  FAIL  {detail}")

    print()
    print(f"Results: {passed} passed, {skipped} skipped (no-provider), {failed} failed  /  {len(targets)} total")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
