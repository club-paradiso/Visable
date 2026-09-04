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

Modules run one per subprocess, under pytest when it is available. Both matter:
subprocess isolation because several modules leak state into each other and a
shared process turns that into order-dependent failures; pytest because it
collects bare test functions as well as unittest.TestCase classes. Under plain
`unittest` a pytest-style module collects ZERO tests and exits 0 — reported as
PASS while asserting nothing. That is how a real source-routing bug sat unseen
for two months. CI installs pytest via backend/requirements-dev.txt, and a
0-collection run is now an error rather than a pass.

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
    # Empty, and that is the point. Every entry here was a real pre-existing
    # failure; each was resolved by deciding whether the ASSERTION had gone
    # stale or the BEHAVIOUR had regressed, and none by deleting or weakening a
    # test:
    #
    #   test_core_journey_ux_hardening   assertion — pinned three literal CSS
    #       strings; the phone rule had been deliberately re-scoped to
    #       `.next-action-panel .next-action-grid` to outrank the 640px rule.
    #       Re-expressed against the behaviour (single column, 44px target).
    #   test_expanded_route_wizard       assertion — pinned a call inside
    #   test_i18n_sweep_route_wizard         selectF4Route, now a back-compat
    #       shim delegating to applyRouteSelection. Re-pointed at the PR #252
    #       invariant: a broad route must not inherit the previous subtype.
    #   test_source_grounding_pipeline   assertion — pinned the 2026-06 stay PDF
    #       superseded by the 2026-07-31 HWP. Now asserts what must hold for any
    #       edition: pinned, present, human-approved, predecessor archived.
    #   test_reentry_procedure_coverage  assertion — written against the 2026-05
    #       pass; the 2026.6 re-sourcing changed doc ids, page ranges and moved
    #       prose into notes. Now asserts provenance, no flattening, and a
    #       retained user-facing caution.
    #
    # Each rewrite was checked by mutating the source to reintroduce the failure
    # it guards and confirming the test fails — a rewritten assertion that
    # cannot fail is worse than the stale one it replaced.
    #
    # Add an entry only with what fails, why it is not fixed here, and who
    # should fix it. A register nobody is forced to shrink is a quieter way of
    # hiding red, which is why a listed test that starts passing also fails the
    # run.
}

# Test modules that need a test-only dependency the backend itself does not
# require. These are reported as SKIP, never silently counted as passing.
#
# These two are pytest-style (bare test functions, no unittest.TestCase). They
# are listed so a machine WITHOUT pytest still reports them honestly rather
# than as passing. With pytest installed — which CI now guarantees via
# backend/requirements-dev.txt — they run normally and this map is unused.
OPTIONAL_DEPENDENCY_MODULES: Dict[str, str] = {
    "test_generalized_evidence_ontology": "pytest",
    "test_generalized_legal_issue_source_planning": "pytest",
}


def discover_modules() -> List[str]:
    return sorted(p.stem for p in TESTS_DIR.glob("test_*.py"))


def _pytest_available() -> bool:
    return subprocess.run(
        [sys.executable, "-c", "import pytest"],
        capture_output=True,
    ).returncode == 0


#: pytest exit code for "no tests were collected". A module that collects
#: nothing has not passed — it has not run. `unittest` reports the same
#: situation as a clean exit 0, which is how a pytest-style module could sit in
#: this suite being counted as PASS while executing zero assertions.
PYTEST_NO_TESTS_COLLECTED = 5


def run_module(name: str, *, use_pytest: bool) -> Dict[str, object]:
    """Run one module in a subprocess so a crash cannot take the runner down.

    One module per process is deliberate and worth the startup cost: several
    modules in this suite leak state into each other (module-level config
    caches, monkeypatched globals), and a single shared process turns that into
    order-dependent failures that have nothing to do with the code under test.

    pytest is used when present because it collects BOTH unittest.TestCase
    classes and bare pytest-style test functions; plain `unittest` silently
    collects zero tests from the latter.
    """
    if use_pytest:
        cmd = [sys.executable, "-m", "pytest", str(TESTS_DIR / f"{name}.py"),
               "-q", "-p", "no:cacheprovider"]
    else:
        cmd = [sys.executable, "-m", "unittest", f"backend.tests.{name}"]

    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    output = (proc.stderr or "") + (proc.stdout or "")
    tail = [line for line in output.strip().splitlines() if line.strip()]
    summary = tail[-1] if tail else ""

    missing_dep = None
    if "ModuleNotFoundError" in output:
        for line in output.splitlines():
            if "ModuleNotFoundError" in line:
                missing_dep = line.split("'")[1] if "'" in line else line.strip()
                break

    collected_nothing = use_pytest and proc.returncode == PYTEST_NO_TESTS_COLLECTED
    if collected_nothing:
        output += (
            "\n\nRUNNER: pytest collected 0 tests from this module. An empty "
            "module is not a passing module — either it lost its tests or its "
            "names no longer match the collection pattern.\n"
        )

    return {
        "module": name,
        "returncode": proc.returncode,
        "summary": summary,
        "missing_dependency": missing_dep,
        "collected_nothing": collected_nothing,
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

    use_pytest = _pytest_available()
    for name in modules:
        outcome = run_module(name, use_pytest=use_pytest)
        ok = outcome["returncode"] == 0 and not outcome["collected_nothing"]
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

    runner_name = "pytest" if use_pytest else "unittest"
    print(f"Backend test suite — {len(modules)} modules (via {runner_name})\n" + "=" * 60)
    if not use_pytest:
        print("  WARNING: pytest is not installed, so this run is DEGRADED.\n"
              "  Modules written as bare pytest functions collect zero tests\n"
              "  under unittest and are reported SKIP, never PASS.\n"
              "  Install backend/requirements-dev.txt for a complete run.\n")
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
