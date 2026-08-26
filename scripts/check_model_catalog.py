#!/usr/bin/env python3
"""Detect stale model configuration against the live provider catalog.

Why
---
Every configured model id is a bet that a catalog Visable does not control
still lists it. Free-tier ids in particular get renamed, deprecated and
withdrawn without notice, and a candidate chain full of dead slugs degrades
silently: each request burns through the chain and lands on the deterministic
fallback, which looks like "the AI is a bit weak today" rather than "the
configuration is wrong".

This reports drift. It does NOT rewrite production model selection — a model
vanishing from a catalog listing for an hour is not a reason to auto-edit what
answers immigration questions. Changing the chain stays a human decision.

Auth
----
OpenRouter's model list is public, so no credential is needed or accepted. If
the catalog cannot be reached the script says so and — without --strict —
exits 0, because "we could not check" is not "the models are gone".

Usage
-----
    python3 scripts/check_model_catalog.py            # report
    python3 scripts/check_model_catalog.py --json
    python3 scripts/check_model_catalog.py --strict   # drift fails the run
    python3 scripts/check_model_catalog.py --offline  # policy lint only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

CATALOG_URL = "https://openrouter.ai/api/v1/models"
TIMEOUT = 30


def load_policy() -> Dict[str, Any]:
    """Every model id this deployment could route to, grouped by task role."""
    from services import ai_runtime as rt  # noqa: WPS433
    from services.model_policy import resolve_answer_mode_models, resolve_model_role_policy

    policy = resolve_model_role_policy()
    roles: Dict[str, List[str]] = {
        role.value: rt.resolve_task_models(role)["candidates"] for role in rt.TaskRole
    }
    tiers = {mode: resolve_answer_mode_models(mode)["candidates"]
             for mode in ("fast", "basic")}
    return {"policy": policy, "roles": roles, "tiers": tiers}


def configured_model_ids(bundle: Dict[str, Any]) -> Dict[str, List[str]]:
    """model id -> the roles/tiers that would route to it."""
    usage: Dict[str, List[str]] = {}
    for role, models in bundle["roles"].items():
        for index, model in enumerate(models):
            usage.setdefault(model, []).append(f"{role}[{index}]")
    for tier, models in bundle["tiers"].items():
        for index, model in enumerate(models):
            usage.setdefault(model, []).append(f"tier:{tier}[{index}]")
    for key in ("router_model", "translation_model", "verifier_model", "chinese_model"):
        value = bundle["policy"].get(key)
        if value:
            usage.setdefault(value, []).append(f"policy:{key}")
    for value in bundle["policy"].get("chinese_fallback_models") or []:
        usage.setdefault(value, []).append("policy:chinese_fallback")
    return usage


def fetch_catalog() -> Dict[str, Any]:
    """Public catalog fetch. Never sends a credential."""
    request = urllib.request.Request(
        CATALOG_URL, headers={"Accept": "application/json", "User-Agent": "visable-catalog-check"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as exc:
        return {"reachable": False, "error": f"{exc.__class__.__name__}: {exc}", "models": {}}

    models: Dict[str, Dict[str, Any]] = {}
    for entry in payload.get("data") or []:
        if not isinstance(entry, dict):
            continue
        model_id = str(entry.get("id") or "").strip()
        if not model_id:
            continue
        pricing = entry.get("pricing") or {}
        models[model_id] = {
            "contextLength": entry.get("context_length"),
            "promptPrice": pricing.get("prompt"),
            "completionPrice": pricing.get("completion"),
            # A ":free" id whose prompt price is not zero has stopped being free.
            "isFree": str(pricing.get("prompt", "")) in {"0", "0.0", "-1"},
        }
    return {"reachable": True, "error": "", "models": models}


def lint_policy(usage: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """Offline checks that need no catalog at all."""
    from services.model_policy import CHINESE_ONLY_MODEL_PREFIXES

    findings: List[Dict[str, str]] = []
    for model, roles in sorted(usage.items()):
        low = model.lower()
        if low.endswith("/auto") or low in {"openrouter/auto", "openrouter/free"}:
            findings.append({"model": model, "issue": "random_routing",
                             "detail": "unauditable model selection", "roles": ", ".join(roles)})
        if "/" not in model:
            findings.append({"model": model, "issue": "malformed_id",
                             "detail": "expected vendor/model", "roles": ", ".join(roles)})
        # China-origin families are reserved for Chinese-language routes; one
        # appearing in a general chain is a policy break, not a catalog issue.
        if any(low.startswith(prefix) for prefix in CHINESE_ONLY_MODEL_PREFIXES):
            general = [r for r in roles if "chinese" not in r.lower()]
            if general:
                findings.append({
                    "model": model, "issue": "chinese_only_model_in_general_chain",
                    "detail": "reserved for Chinese-language routes by policy",
                    "roles": ", ".join(general)})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Catalog drift and policy findings fail the run.")
    parser.add_argument("--offline", action="store_true",
                        help="Policy lint only; do not contact the catalog.")
    args = parser.parse_args()

    bundle = load_policy()
    usage = configured_model_ids(bundle)
    policy_findings = lint_policy(usage)

    catalog = {"reachable": False, "error": "offline mode", "models": {}} if args.offline \
        else fetch_catalog()

    missing: List[Dict[str, Any]] = []
    no_longer_free: List[Dict[str, Any]] = []
    present: List[str] = []

    if catalog["reachable"]:
        known: Set[str] = set(catalog["models"])
        for model, roles in sorted(usage.items()):
            if model not in known:
                missing.append({"model": model, "roles": roles})
                continue
            present.append(model)
            entry = catalog["models"][model]
            if model.endswith(":free") and not entry["isFree"]:
                no_longer_free.append({"model": model, "roles": roles,
                                       "promptPrice": entry["promptPrice"]})

    # A chain whose every candidate is gone cannot answer at all — much more
    # serious than one dead fallback, so it is reported separately.
    dead_chains: List[Dict[str, Any]] = []
    if catalog["reachable"]:
        known = set(catalog["models"])
        for role, models in {**bundle["roles"],
                             **{f"tier:{k}": v for k, v in bundle["tiers"].items()}}.items():
            if models and not any(m in known for m in models):
                dead_chains.append({"role": role, "candidates": models})

    exit_code = 0
    if args.strict and (missing or policy_findings or dead_chains):
        exit_code = 1
    if args.strict and not catalog["reachable"] and not args.offline:
        exit_code = 1

    if args.json:
        print(json.dumps({
            "catalogReachable": catalog["reachable"],
            "catalogError": catalog["error"],
            "configuredModelCount": len(usage),
            "presentCount": len(present),
            "missing": missing,
            "noLongerFree": no_longer_free,
            "deadChains": dead_chains,
            "policyFindings": policy_findings,
            "policyVersion": bundle["policy"]["version"],
            "exitCode": exit_code,
        }, ensure_ascii=False, indent=2))
        return exit_code

    print("Visable model-catalog check")
    print("=" * 62)
    print(f"  policy version      {bundle['policy']['version']}")
    print(f"  configured models   {len(usage)}")

    if not catalog["reachable"]:
        print(f"  catalog             UNREACHABLE ({catalog['error']})")
        print("\n  CATALOG NOT VERIFIED — model availability was not checked.")
        print("  This is not evidence that the configured models are fine.")
    else:
        print(f"  catalog             reachable ({len(catalog['models'])} models listed)")
        print(f"  present             {len(present)}/{len(usage)}")

        if missing:
            print(f"\n  MISSING FROM CATALOG ({len(missing)}):")
            for entry in missing:
                print(f"    - {entry['model']}")
                print(f"        routed by: {', '.join(entry['roles'])}")
        if dead_chains:
            print(f"\n  DEAD CHAINS ({len(dead_chains)}) — no candidate exists, "
                  f"this role cannot answer:")
            for entry in dead_chains:
                print(f"    - {entry['role']}: {', '.join(entry['candidates'])}")
        if no_longer_free:
            print(f"\n  NO LONGER FREE ({len(no_longer_free)}) — a ':free' id now prices:")
            for entry in no_longer_free:
                print(f"    - {entry['model']}  prompt={entry['promptPrice']}")
            print("    Review before deploying: this changes the cost posture.")

    if policy_findings:
        print(f"\n  POLICY FINDINGS ({len(policy_findings)}):")
        for finding in policy_findings:
            print(f"    - [{finding['issue']}] {finding['model']}")
            print(f"        {finding['detail']} (in {finding['roles']})")

    if catalog["reachable"] and not (missing or dead_chains or no_longer_free or policy_findings):
        print("\n  OK — every configured model is listed and policy-conformant.")
    elif not args.strict:
        print("\n  Reported only. Model selection is NOT auto-edited: changing what "
              "answers\n  immigration questions stays a human decision. "
              "Use --strict to gate on this.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
