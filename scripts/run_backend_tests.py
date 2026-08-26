#!/usr/bin/env python3
"""Run the WHOLE backend test suite and report the result honestly.

The problem this solves
-----------------------
`scripts/check_repo.sh` ran 5 of the 47 backend test modules. The other 42 were
committed, maintained, and never executed by CI. Thirteen of them were failing
on main — including every suite covering AI provider routing, the unified
search API, and employment interpretation — while the repository check printed
"Success: repository validation passed."

That is how two production endpoints stayed completely broken through many
green builds: the tests that could have caught them either did not exist or
were never run.

What this runner does
---------------------
Runs every `backend/tests/test_*.py` module and classifies each one:

  PASS       — ran clean.
  KNOWN      — failing, and listed in KNOWN_FAILING below with a reason.
  NEW        — failing and NOT listed. This fails the run.
  FIXED      — listed as known-failing but now passing. This ALSO fails the
               run, so the register cannot rot into a permanent excuse list.
  SKIP       — could not be imported for an environmental reason (a missing
               optional test-only dependency), reported explicitly.

The register is the point. "Known failing" is only honest if it is dated,
justified, and self-expiring; a list nobody is forced to shrink is just a
quieter way of hiding red.

Usage:
    python3 scripts/run_backend_tests.py            # honest full run
    python3 scripts/run_backend_tests.py --strict   # KNOWN failures also fail
    python3 scripts/run_backend_tests.py --json     # machine-readable report
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "backend" / "tests"

# ---------------------------------------------------------------------------
# Known-failing register
# ---------------------------------------------------------------------------
# Every entry needs: what fails, why it is not fixed here, and who should fix
# it. These are all PRE-EXISTING failures on main, in deterministic UI/data
# areas untouched by the AI-architecture work that introduced this runner.
# They are recorded rather than repaired because repairing them means editing
# protected data files or reverting deliberate frontend refactors — decisions
# that belong to the people who made them, not to a drive-by fix.
KNOWN_FAILING: Dict[str, str] = {
    "test_core_journey_ux_hardening": (
        "Asserts the literal CSS rule '.next-action-grid { grid-template-columns: 1fr; }' "
        "in index.html. The narrow-screen action surface was restyled and the rule no "
        "longer exists in that form. Frontend owner should re-express the assertion "
        "against the current responsive rule, or restore it if the behaviour regressed."
    ),
    "test_expanded_route_wizard": (
        "Asserts the inline call \"applyScenarioSelection(selector, variantId || '')\" "
        "inside selectF4Route, which has since been refactored into a back-compat shim "
        "that resolves the wizard from the clicked control. Route-wizard owner should "
        "re-point the assertion at the shim's real delegation path."
    ),
    "test_i18n_sweep_route_wizard": (
        "Same selectF4Route refactor as test_expanded_route_wizard."
    ),
    "test_source_grounding_pipeline": (
        "Asserts the manual manifest points at docs/source-manuals/2026-06/"
        "stay_manual_2026_06_01.pdf. PR #562 superseded that edition with the "
        "2026-07-31 distribution HWP, so the assertion now describes a retired "
        "source. Manual-sourcing owner should re-point it at the current edition."
    ),
    "test_reentry_procedure_coverage": (
        "Rendered document lists contain the raw doc_master id 'doc_fee_generic' where "
        "the test expects a resolved fee label. The id IS valid in doc_master.json, so "
        "this is a resolution gap between the packet builder and the renderer, not data "
        "corruption. Worth fixing — an unresolved id reaching a user-facing list is "
        "exactly the misleading-rendering class CLAUDE.md guards against — but it needs "
        "a doc-resolution owner, not an AI-architecture change."
    ),
    "test_scenario_procedure_variants": (
        "Same doc_fee_generic resolution gap, plus a spacing change in "
        "'통합신청서 (별지 제34호 서식)' vs '통합신청서(별지 제34호 서식)'."
    ),
}

# Test modules that need a test-only dependency the backend itself does not
# require. These are reported as SKIP, never silently counted as passing.
OPTIONAL_DEPENDENCY_MODULES: Dict[str, str] = {
    "test_generalized_evidence_ontology": "pytest",
    "test_generalized_legal_issue_source_planning": "pytest",
}


def discover_modules() -> List[str]:
    return sorted(p.stem for p in TESTS_DIR.glob("test_*.py"))


def run_module(name: str) -> Dict[str, object]:
    """Run one module in a subprocess so a crash cannot take the runner down."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", f"backend.tests.{name}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = (proc.stderr or "") + (proc.stdout or "")
    tail = [line for line in output.strip().splitlines() if line.strip()]
    summary = tail[-1] if tail else ""

    missing_dep = None
    if "ModuleNotFoundError" in output:
        for line in output.splitlines():
            if "ModuleNotFoundError" in line:
                missing_dep = line.split("'")[1] if "'" in line else line.strip()
                break

    return {
        "module": name,
        "returncode": proc.returncode,
        "summary": summary,
        "missing_dependency": missing_dep,
        "output": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true",
                        help="Fail on registered known failures too (release gate).")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--only", default="", help="Comma-separated module names.")
    args = parser.parse_args()

    modules = discover_modules()
    if args.only:
        wanted = {m.strip() for m in args.only.split(",") if m.strip()}
        modules = [m for m in modules if m in wanted]

    results: Dict[str, List[str]] = {
        "pass": [], "known": [], "new": [], "fixed": [], "skip": [],
    }
    details: List[Dict[str, object]] = []
    failure_output: Dict[str, str] = {}

    for name in modules:
        outcome = run_module(name)
        ok = outcome["returncode"] == 0
        dep = outcome["missing_dependency"]
        expected_dep = OPTIONAL_DEPENDENCY_MODULES.get(name)

        if not ok and dep and expected_dep and dep == expected_dep:
            bucket = "skip"
        elif ok and name in KNOWN_FAILING:
            bucket = "fixed"
        elif ok:
            bucket = "pass"
        elif name in KNOWN_FAILING:
            bucket = "known"
        else:
            bucket = "new"
            failure_output[name] = str(outcome["output"])[-4000:]

        results[bucket].append(name)
        details.append({
            "module": name, "bucket": bucket, "summary": outcome["summary"],
            "missing_dependency": dep,
        })

    # A registered failure that now passes must be removed from the register,
    # or the register stops meaning anything.
    exit_code = 0
    if results["new"] or results["fixed"]:
        exit_code = 1
    if args.strict and results["known"]:
        exit_code = 1

    if args.json:
        print(json.dumps({
            "modules_run": len(modules),
            "results": results,
            "details": details,
            "strict": args.strict,
            "exit_code": exit_code,
        }, ensure_ascii=False, indent=2))
        return exit_code

    print(f"Backend test suite — {len(modules)} modules\n" + "=" * 60)
    print(f"  PASS   {len(results['pass']):>3}")
    print(f"  KNOWN  {len(results['known']):>3}  (registered pre-existing failures)")
    print(f"  SKIP   {len(results['skip']):>3}  (optional test-only dependency absent)")
    print(f"  NEW    {len(results['new']):>3}  <- regressions")
    print(f"  FIXED  {len(results['fixed']):>3}  <- remove from the register")

    if results["skip"]:
        print("\nSKIPPED (optional dependency not installed):")
        for name in results["skip"]:
            print(f"  - {name}: needs {OPTIONAL_DEPENDENCY_MODULES.get(name, '?')}")
        print("  These are NOT counted as passing. Install the dependency to run them.")

    if results["known"]:
        print("\nKNOWN PRE-EXISTING FAILURES (tracked, not hidden):")
        for name in results["known"]:
            print(f"  - {name}\n      {KNOWN_FAILING[name]}")

    if results["fixed"]:
        print("\nERROR: these are registered as known-failing but now PASS.")
        print("Remove them from KNOWN_FAILING so the register keeps its meaning:")
        for name in results["fixed"]:
            print(f"  - {name}")

    if results["new"]:
        print("\nERROR: NEW failures not in the register (regressions):")
        for name in results["new"]:
            print(f"\n----- {name} -----")
            print(failure_output.get(name, "")[-2000:])

    if exit_code == 0 and results["known"]:
        print("\nResult: no regressions. "
              f"{len(results['known'])} pre-existing failures remain registered "
              "— this run is NOT a clean suite.")
    elif exit_code == 0:
        print("\nResult: full backend suite clean.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
