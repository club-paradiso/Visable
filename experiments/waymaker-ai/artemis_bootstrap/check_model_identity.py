"""CI guard for active Waymaker Artemis executable/configuration paths.

Historical documents, archived run data, policy research and negative test
fixtures are classified separately. This is not a scan of other Visable apps.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from waymaker_ai import foundation
from waymaker_ai.distillation import experiment_config

FORBIDDEN = re.compile(r"gemma[-_ ]?3|gemma3|270m|gemma[-_ ]?2|qwen", re.I)
SUFFIXES = {".py", ".sh", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".cfg", ".env"}
EXCEPTIONS = {
    "configs/teacher_policy.json": "External teacher licensing/policy catalogue, not an inference selector",
    "tests/test_teacher_policy.py": "Teacher policy fixtures",
    "tests/test_artemis_foundation.py": "Explicit rejection tests",
    "artemis_bootstrap/check_model_identity.py": "Guard pattern itself",
    "artemis_bootstrap/WAYMAKER-ARTEMIS-LOCAL-CLEANUP-MANIFEST.json": "Recovery inventory and historical paths",
    "artemis_bootstrap/PR-726-REVIEW-COVERAGE.json": "Post-audit review inventory of the exact 78 baseline PR paths",
}


def audit(root: Path = ROOT) -> dict:
    violations, permitted, checked = [], [], 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or (path.suffix not in SUFFIXES and not path.name.startswith(".env")):
            continue
        relative = path.relative_to(root)
        if any(p in {".git", ".venv", "node_modules", "__pycache__"} for p in relative.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not FORBIDDEN.search(text):
            checked += 1
            continue
        name = relative.as_posix()
        reason = EXCEPTIONS.get(name)
        if name.startswith("artemis_bootstrap/history/"):
            reason = "Historical record outside active run discovery"
        if reason:
            permitted.append({"path": name, "classification": reason})
        else:
            violations.append(name)
    foundation.configuration()
    for name in ("gemma4_e4b", "gemma4_e2b"):
        foundation.profile(name)
    for path in experiment_config.config_paths():
        experiment_config.load_config(path)
    # The same policy must protect both inference entry points.
    for name in ("artemis_runner.py", "run_smoke.py"):
        text = (root / "artemis_bootstrap" / name).read_text()
        if "foundation.select_profile" not in text:
            violations.append(f"{name}: missing canonical profile selection")
        if "from mlx_lm import" in text:
            violations.append(f"{name}: legacy runtime selection")
    judge = (root / "artemis_bootstrap" / "flip_judge.py")
    if judge.exists():
        text = judge.read_text()
        if "LocalModelAdapter" not in text or "project_inference_item" not in text:
            violations.append("flip_judge.py: missing shared model/input preflight")
        if "snapshot_download" in text or "from mlx_lm import" in text:
            violations.append("flip_judge.py: unguarded legacy loader")
    return {"status": "FAIL" if violations else "PASS", "checked_files": checked,
            "violations": violations, "permitted_mentions": permitted}


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["violations"]))
