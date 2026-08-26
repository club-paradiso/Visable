from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.grounding_config import load_grounding_config  # noqa: E402


LAW_ENV = ("LAW_API_OC", "LAW_OC", "OPEN_LAW_ID", "LAW_API_KEY")


def clear_law_env() -> None:
    for key in LAW_ENV:
        os.environ.pop(key, None)


def setup_function() -> None:
    clear_law_env()


def teardown_function() -> None:
    clear_law_env()


def test_law_oc_alias_is_accepted() -> None:
    os.environ["LAW_OC"] = "alias-value"
    cfg = load_grounding_config()
    assert cfg.law_api_credential == "alias-value"
    assert cfg.law_api_credential_source == "LAW_OC"
    assert "LAW_API_OC_ALIAS_USED" in cfg.warnings


def test_open_law_id_alias_is_accepted() -> None:
    os.environ["OPEN_LAW_ID"] = "mcp-value"
    cfg = load_grounding_config()
    assert cfg.law_api_credential == "mcp-value"
    assert cfg.law_api_credential_source == "OPEN_LAW_ID"
    assert "LAW_API_OC_ALIAS_USED" in cfg.warnings


def test_canonical_oc_wins_over_aliases_and_legacy_key() -> None:
    os.environ["LAW_API_OC"] = "canonical"
    os.environ["LAW_OC"] = "alias"
    os.environ["OPEN_LAW_ID"] = "mcp"
    os.environ["LAW_API_KEY"] = "legacy"
    cfg = load_grounding_config()
    assert cfg.law_api_credential == "canonical"
    assert cfg.law_api_credential_source == "LAW_API_OC"
    assert "LAW_API_OC_ALIAS_USED" not in cfg.warnings
