"""The backend must work from a copy of ``backend/`` alone (Railway context).

Railway builds with Root Directory = ``backend``, so repository-root files are
absent in production. After the knowledge platform (#644) started reading
``data/source_registry.json`` and friends from the repository root, the Railway
deploy came up with an empty knowledge store: manual grounding returned
``None`` and the Fast "D-2 연장시 필수 서류" answer lost its source-confirmed
structured checklist, while every in-repo test still passed. Railway Live
Smoke #73 caught it (``WAYMAKER_FAST_PUBLIC_CONTRACT: no structured_answer``).

These tests reproduce the production layout by copying ``backend/`` into a
temporary directory with no repository root around it and running the real
``/api/ask`` request in a subprocess.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parent

_PROBE = r'''
import json, sys
sys.path.insert(0, ".")
from unittest.mock import patch
from fastapi.testclient import TestClient
import paradiso_backend as pb
from services.model_policy import resolve_answer_mode_models

# Production state from Railway Live Smoke #73: every Fast model cooling down.
pb._reset_openrouter_model_cooldowns_for_tests()
for model in resolve_answer_mode_models("fast")["candidates"]:
    pb._mark_openrouter_model_cooling_down(model)
with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"):
    resp = TestClient(pb.app).post("/api/ask", json={
        "question": "D-2 연장시 필수 서류", "visa_code": "D-2",
        "answer_mode": "fast", "stream": False,
    })
body = resp.json()
docs = ((body.get("structured_answer") or {}).get("required_documents") or {})
print("PROBE" + json.dumps({
    "status": resp.status_code,
    "grounding_used": body.get("grounding_used"),
    "structured": bool(body.get("structured_answer")),
    "common": [d.get("label") for d in docs.get("common") or []],
    "conditional": len(docs.get("conditional") or []),
    "required": len(docs.get("required") or []),
    "fallback_answer_kind": body.get("fallback_answer_kind"),
}, ensure_ascii=False))
'''


class BackendOnlyDeployContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        deploy = Path(cls._tmp.name) / "app"
        shutil.copytree(BACKEND, deploy, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", "tests",
        ))
        (deploy / "probe.py").write_text(_PROBE, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in {"OPENROUTER_API_KEY", "GROQ_API_KEY"}}
        run = subprocess.run(
            [sys.executable, "probe.py"], cwd=deploy, env=env,
            capture_output=True, text=True, timeout=600,
        )
        cls.stderr = run.stderr
        line = next((ln for ln in run.stdout.splitlines() if ln.startswith("PROBE")), None)
        cls.result = json.loads(line[len("PROBE"):]) if line else None
        cls.returncode = run.returncode

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_probe_ran(self):
        self.assertEqual(self.returncode, 0, self.stderr[-4000:])
        self.assertIsNotNone(self.result, self.stderr[-4000:])

    def test_knowledge_platform_boots_from_deploy_copies(self):
        self.assertNotIn("knowledge_platform_init_failed", self.stderr)

    def test_fast_d2_keeps_manual_grounding_and_structured_answer(self):
        r = self.result or {}
        self.assertEqual(r.get("status"), 200, self.stderr[-2000:])
        self.assertTrue(r.get("grounding_used"), r)
        self.assertTrue(r.get("structured"), r)
        self.assertEqual(r.get("common"), ["신청서", "여권", "외국인등록증", "수수료"])
        self.assertGreaterEqual(r.get("conditional") or 0, 1)
        self.assertGreaterEqual(r.get("required") or 0, 1)
        self.assertEqual(r.get("fallback_answer_kind"), "structured_document_checklist")


class DeployCopyCoverageTests(unittest.TestCase):
    """Every repository-root file the backend reads has a synced deploy copy."""

    def _pairs(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import sync_visa_data  # noqa: WPS433
        finally:
            sys.path.pop(0)
        return {src.relative_to(REPO_ROOT).as_posix() for src, _ in sync_visa_data.SYNCED_PAIRS}

    def test_every_manual_corpus_file_is_synced(self):
        synced = self._pairs()
        corpus = sorted(p.relative_to(REPO_ROOT).as_posix()
                        for p in (REPO_ROOT / "data" / "manual-corpus").glob("*.json"))
        self.assertTrue(corpus)
        missing = [p for p in corpus if p not in synced]
        self.assertEqual(missing, [], "add these to scripts/sync_visa_data.py SYNCED_PAIRS")

    def test_knowledge_inputs_are_synced(self):
        synced = self._pairs()
        for rel in ("data/source_registry.json", "data/manual_approval_index.json",
                    "data/status-guidance-202609.json", "doc_master.json"):
            self.assertIn(rel, synced)


if __name__ == "__main__":
    unittest.main()
