from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.grounding_config import load_grounding_config  # noqa: E402

LAW_ENV_NAMES = ("LAW_API_OC", "LAW_OC", "OPEN_LAW_ID", "LAW_API_KEY")


def _env(**values: str):
    clean = {name: "" for name in LAW_ENV_NAMES}
    clean.update(values)
    return patch.dict(os.environ, clean, clear=False)


def test_python_placeholder_oc_does_not_shadow_legacy_key():
    with _env(LAW_API_OC="paradiso", LAW_API_KEY="registered-legacy-oc"):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "registered-legacy-oc"
    assert cfg.law_api_credential_source == "LAW_API_KEY"
    assert "LAW_API_OC_PLACEHOLDER_DETECTED" in cfg.warnings
    assert "LAW_API_OC_PLACEHOLDER_IGNORED_FOR_KEY_FALLBACK" in cfg.warnings


def test_python_real_alias_beats_historical_placeholder():
    with _env(LAW_API_OC="paradiso", LAW_OC="registered-current-oc"):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "registered-current-oc"
    assert cfg.law_api_credential_source == "LAW_OC"
    assert "LAW_API_OC_PLACEHOLDER_DETECTED" in cfg.warnings


def test_python_real_primary_still_wins():
    with _env(LAW_API_OC="registered-primary-oc", LAW_API_KEY="registered-legacy-oc"):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "registered-primary-oc"
    assert cfg.law_api_credential_source == "LAW_API_OC"


def test_node_resolver_matches_python_placeholder_policy():
    if not shutil.which("node"):
        return
    script = r"""
const { resolveLawCredential } = require('./lib/law-credential');
const cases = [
  resolveLawCredential({ LAW_API_OC: 'paradiso', LAW_API_KEY: 'registered-legacy-oc' }),
  resolveLawCredential({ LAW_API_OC: 'paradiso', LAW_OC: 'registered-current-oc' }),
  resolveLawCredential({ LAW_API_OC: 'registered-primary-oc', LAW_API_KEY: 'registered-legacy-oc' }),
];
process.stdout.write(JSON.stringify(cases));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    cases = json.loads(result.stdout)
    assert cases[0]["credential"] == "registered-legacy-oc"
    assert cases[0]["credentialSource"] == "LAW_API_KEY"
    assert cases[0]["ignoredPlaceholderSource"] == "LAW_API_OC"
    assert cases[1]["credential"] == "registered-current-oc"
    assert cases[1]["credentialSource"] == "LAW_OC"
    assert cases[2]["credential"] == "registered-primary-oc"
    assert cases[2]["credentialSource"] == "LAW_API_OC"
