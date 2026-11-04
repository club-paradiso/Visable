"""API contract snapshot for the Phase 6 backend split (docs/rebuild/DECISIONS.md ADR-013).

The route handlers of paradiso_backend.py move into backend/routers/*.py. This test pins the
public HTTP contract that must not move with them: the full OpenAPI document (paths, operations,
request/response schemas, operationIds, dependencies' effects on the schema), the ordered route
table (path, methods, endpoint name), the middleware stack and the exception handlers. The
snapshot was generated before the first handler moved (``--update`` regenerates it on purpose;
a diff in review is the point).

Run: python3 -m pytest backend/tests/test_api_contract_snapshot.py -q
Update (deliberate contract change only): python3 backend/tests/test_api_contract_snapshot.py --update
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SNAPSHOT = Path(__file__).resolve().parent / "fixtures" / "api_contract_snapshot.json"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402


def _route_table():
    rows = []
    for r in pb.app.routes:
        methods = sorted(getattr(r, "methods", None) or [])
        endpoint = getattr(r, "endpoint", None)
        rows.append({
            "path": getattr(r, "path", ""),
            "methods": methods,
            "name": getattr(r, "name", ""),
            "endpoint": getattr(endpoint, "__name__", "") if endpoint is not None else "",
            "include_in_schema": bool(getattr(r, "include_in_schema", True)),
        })
    return rows


def current_contract():
    return {
        "openapi": pb.app.openapi(),
        "routes": _route_table(),
        "middleware": [getattr(m.cls, "__name__", str(m.cls)) for m in pb.app.user_middleware],
        "exception_handlers": sorted(
            getattr(k, "__name__", str(k)) if not isinstance(k, int) else str(k) for k in pb.app.exception_handlers
        ),
        "title": pb.app.title,
        "version": pb.app.version,
    }


class ApiContractSnapshotTests(unittest.TestCase):
    def test_contract_matches_snapshot(self):
        self.assertTrue(SNAPSHOT.exists(), f"missing snapshot {SNAPSHOT}; run this file with --update once, before any handler moves")
        expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        actual = json.loads(json.dumps(current_contract(), sort_keys=True))
        for key in ("title", "version", "middleware", "exception_handlers"):
            self.assertEqual(expected[key], actual[key], key)
        self.assertEqual(
            [(r["path"], tuple(r["methods"]), r["name"], r["endpoint"]) for r in expected["routes"]],
            [(r["path"], tuple(r["methods"]), r["name"], r["endpoint"]) for r in actual["routes"]],
            "route table (order, path, methods, endpoint name) changed",
        )
        exp_paths, act_paths = expected["openapi"]["paths"], actual["openapi"]["paths"]
        self.assertEqual(sorted(exp_paths), sorted(act_paths), "OpenAPI path set changed")
        for path in exp_paths:
            self.assertEqual(exp_paths[path], act_paths[path], f"OpenAPI operation changed: {path}")
        self.assertEqual(expected["openapi"].get("components"), actual["openapi"].get("components"), "OpenAPI component schemas changed")
        self.assertEqual(expected["openapi"], actual["openapi"], "OpenAPI document changed")

    def test_snapshot_covers_every_handler_group(self):
        # Every route the app serves is in the snapshot (no silent additions).
        expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(len(expected["routes"]), len(pb.app.routes))


if __name__ == "__main__":
    if "--update" in sys.argv:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(current_contract(), indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", SNAPSHOT)
    else:
        unittest.main()
