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
from services.knowledge import ingestion, guard
print(json.dumps({
    "repo_root_has_data": (paths.REPO_ROOT / "data" / "source_registry.json").exists(),
    "seed": platform.bootstrap_report.get("seed"),
    "grounding": grounding is not None,
    "documents": len((grounding or {}).get("required_documents") or []),
    "status_universe": len(ingestion.status_universe()),
    "document_vocabulary": len(guard.document_vocabulary()),
}))
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


if __name__ == "__main__":
    unittest.main()
