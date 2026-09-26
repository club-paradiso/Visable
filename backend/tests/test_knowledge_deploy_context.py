"""The knowledge platform must work in the Railway deploy context.

Railway deploys the backend with Root Directory = backend, so nothing at the
repository root (data/…, doc_master.json) is in the build context. Before this
guard the platform bootstrap read ``<repo root>/data/source_registry.json``,
raised FileNotFoundError on every request in production, and /api/ask lost
the manual grounding (no structured D-2 checklist) while every in-repo test
stayed green. This test runs the platform from a backend-only copy.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

_PROBE = r"""
import json, sys
from services.knowledge import paths
from services.knowledge.runtime import KnowledgePlatform
platform = KnowledgePlatform.create(":memory:")
grounding = platform.grounding_for("D-2", "extension", None)
from services.knowledge import ingestion, guard, evidence, adapters
from services import manual_registry
versions = manual_registry.load_manual_versions()

# The Fast public /api/ask request in the state Railway Live Smoke #73 saw:
# every Fast model cooling down (the model contributes nothing).
from unittest.mock import patch
from fastapi.testclient import TestClient
import paradiso_backend as pb
from services.model_policy import resolve_answer_mode_models
for model in resolve_answer_mode_models("fast")["candidates"]:
    pb._mark_openrouter_model_cooling_down(model)
with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"):
    ask = TestClient(pb.app).post("/api/ask", json={
        "question": "D-2 연장시 필수 서류", "visa_code": "D-2",
        "answer_mode": "fast", "stream": False,
    })
ask_body = ask.json()
docs = ((ask_body.get("structured_answer") or {}).get("required_documents") or {})
print(json.dumps({
    "repo_root_has_data": (paths.REPO_ROOT / "data" / "source_registry.json").exists(),
    "seed": platform.bootstrap_report.get("seed"),
    "grounding": grounding is not None,
    "documents": len((grounding or {}).get("required_documents") or []),
    "status_universe": len(ingestion.status_universe()),
    "document_vocabulary": len(guard.document_vocabulary()),
    "manual_versions": len(versions),
    "manual_approved": sum(1 for v in versions if v.approval_state == "approved"),
    "corpus_pages": adapters._corpus_page_count("stay_manual_2026_09_18_pdf"),
    "evidence_corpus": bool(evidence._corpus("stay_manual_2026_09_18_pdf")),
    "ask_status": ask.status_code,
    "ask_grounding_used": ask_body.get("grounding_used"),
    "ask_structured": bool(ask_body.get("structured_answer")),
    "ask_common": [d.get("label") for d in docs.get("common") or []],
}, ensure_ascii=False))
"""


class KnowledgeDeployContextTests(unittest.TestCase):
    def test_backend_only_tree_bootstraps_and_grounds_d2_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "app"
            shutil.copytree(
                BACKEND_DIR, app,
                ignore=shutil.ignore_patterns("tests", "var", "__pycache__", "*.pyc"),
            )
            result = subprocess.run(
                [sys.executable, "-c", _PROBE], cwd=app, capture_output=True, text=True,
                timeout=300, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        report = json.loads(result.stdout.strip().splitlines()[-1])
        # The probe really ran without the repository root.
        self.assertFalse(report["repo_root_has_data"])
        self.assertTrue(report["grounding"], report)
        self.assertGreater(report["documents"], 0, report)
        self.assertGreater(report["status_universe"], 0, report)
        self.assertGreater(report["document_vocabulary"], 0, report)
        # Manual registry (manual search / registry status): production saw
        # zero versions, so every manual fell back to needs_review.
        self.assertGreater(report["manual_versions"], 0, report)
        self.assertGreater(report["manual_approved"], 0, report)
        # Manual page corpus (edition page counts, source-evidence excerpts).
        self.assertTrue(report["corpus_pages"], report)
        self.assertTrue(report["evidence_corpus"], report)
        # The public Fast D-2 contract with no usable model.
        self.assertEqual(report["ask_status"], 200, report)
        self.assertTrue(report["ask_grounding_used"], report)
        self.assertTrue(report["ask_structured"], report)
        self.assertEqual(report["ask_common"], ["신청서", "여권", "외국인등록증", "수수료"], report)


if __name__ == "__main__":
    unittest.main()
