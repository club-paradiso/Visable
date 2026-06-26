#!/usr/bin/env python3
"""Live smoke test for the Open Law API (law.go.kr) behind LAW_API_OC.

This makes REAL network calls and is intentionally NOT part of the offline test
suite (unit tests mock the transport). Run it manually with a real credential:

    LAW_API_OC=... python3 scripts/smoke_legal_api.py

It exercises the same OC-safe adapters the /api/legal endpoints use
(law_tools.search_laws, precedent_sources.search_precedents) across the
representative immigration queries, and prints per-query status + a couple of
sample titles. The OC value is never printed (the adapters OC-redact URLs).

Exit codes:
  0  — all queries returned a result OR a clean "no results"/graceful state,
       OR LAW_API_OC is not set (nothing to smoke; reported and skipped).
  1  — at least one query hit a transport/parse error (law API reachability).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.grounding_config import load_grounding_config  # noqa: E402
from services.law_tools import search_laws  # noqa: E402
from services import precedent_sources  # noqa: E402

QUERIES = [
    "출입국관리법",
    "체류자격 변경",
    "강제퇴거",
    "체류기간 연장 불허",
    "귀화 불허",
]


def main() -> int:
    cfg = load_grounding_config()
    if not cfg.law_api_configured:
        print("LAW_API_OC (or legacy LAW_API_KEY) is not set — nothing to smoke. Skipping.")
        print("Run with:  LAW_API_OC=... python3 scripts/smoke_legal_api.py")
        return 0

    print("Open Law API live smoke — credential source: %s" % (cfg.law_api_credential_source or "?"))
    print("=" * 64)
    transport_errors = 0

    for q in QUERIES:
        print("\n[QUERY] %s" % q)

        law = search_laws(q, limit=3, config=cfg)
        status = law.get("status")
        count = law.get("result_count", 0)
        if status == "ok":
            print("  laws: ok (%d)" % count)
            for r in (law.get("results") or [])[:2]:
                print("    - %s" % (r.get("title") or r.get("law_name") or "(law)"))
        else:
            et = law.get("error_type") or "?"
            print("  laws: %s (%s)" % (status, et))
            if et in ("law_api_http_error", "law_api_timeout", "law_api_bad_response", "law_api_parse_error"):
                transport_errors += 1

        prec = precedent_sources.search_precedents(q, limit=3, config=cfg)
        pstatus = prec.get("status")
        pcount = prec.get("itemCount", 0)
        if pstatus in ("results_found", "no_results"):
            print("  precedents: %s (%d)" % (pstatus, pcount))
            for it in (prec.get("items") or [])[:2]:
                if it.get("title"):
                    print("    - %s" % it.get("title"))
        else:
            print("  precedents: %s (%s)" % (pstatus, prec.get("errorType") or "?"))
            if pstatus in ("http_error", "timeout", "bad_response", "parse_error", "official_error"):
                transport_errors += 1

    print("\n" + "=" * 64)
    if transport_errors:
        print("SMOKE: %d transport/parse error(s) — check law.go.kr reachability + OC value." % transport_errors)
        return 1
    print("SMOKE: OK — all queries returned a result or a graceful no-results state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
