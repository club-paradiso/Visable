from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import law_tools as lt  # noqa: E402
from services.grounding_config import load_grounding_config  # noqa: E402

LAW_ENV_NAMES = ("LAW_API_OC", "LAW_OC", "OPEN_LAW_ID", "LAW_API_KEY")
RAILWAY_ENV_NAMES = (
    "RAILWAY_PROJECT_ID",
    "RAILWAY_ENVIRONMENT_ID",
    "RAILWAY_SERVICE_ID",
    "RAILWAY_PUBLIC_DOMAIN",
)


def _env(**values: str):
    clean = {name: "" for name in (*LAW_ENV_NAMES, *RAILWAY_ENV_NAMES)}
    clean.update(values)
    return patch.dict(os.environ, clean, clear=False)


class _RecordingTransport:
    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float) -> lt.LawHttpResponse:
        self.urls.append(url)
        return lt.LawHttpResponse(
            ok=True,
            status_code=200,
            text='{"LawSearch":{"law":[{"법령명한글":"출입국관리법","법령ID":"001386"}]}}',
        )


def test_non_railway_preserves_existing_oc_first_contract():
    with _env(LAW_API_OC="paradiso", LAW_API_KEY="registered-legacy-oc"):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "paradiso"
    assert cfg.law_api_credential_source == "LAW_API_OC"
    assert cfg.law_api_oc_configured is True
    assert cfg.law_api_key_fallback_configured is True


def test_railway_placeholder_oc_falls_back_to_existing_legacy_key():
    with _env(
        RAILWAY_SERVICE_ID="service-test",
        LAW_API_OC="paradiso",
        LAW_API_KEY="registered-legacy-oc",
    ):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "registered-legacy-oc"
    assert cfg.law_api_credential_source == "LAW_API_KEY"
    assert cfg.law_api_oc_configured is False
    assert cfg.law_api_key_fallback_configured is True
    assert "LAW_API_OC_PLACEHOLDER_DETECTED_ON_RAILWAY" in cfg.warnings
    assert "LAW_API_OC_PLACEHOLDER_IGNORED_FOR_RAILWAY_KEY_FALLBACK" in cfg.warnings
    assert "LAW_API_OC_RECOMMENDED" in cfg.warnings


def test_railway_fallback_key_is_used_in_actual_law_request():
    with _env(
        RAILWAY_ENVIRONMENT_ID="environment-test",
        LAW_API_OC="paradiso",
        LAW_API_KEY="registered-legacy-oc",
    ):
        cfg = load_grounding_config()
        transport = _RecordingTransport()
        result = lt.search_laws("출입국관리법", config=cfg, transport=transport)
    assert result["status"] == "ok"
    assert transport.urls
    assert "OC=registered-legacy-oc" in transport.urls[0]
    assert "OC=paradiso" not in transport.urls[0]
    assert "registered-legacy-oc" not in result["source_url"]


def test_railway_real_oc_alias_beats_historical_primary_placeholder():
    with _env(
        RAILWAY_ENVIRONMENT_ID="environment-test",
        LAW_API_OC="paradiso",
        LAW_OC="registered-current-oc",
        LAW_API_KEY="registered-legacy-oc",
    ):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "registered-current-oc"
    assert cfg.law_api_credential_source == "LAW_OC"
    assert cfg.law_api_oc_configured is True
    assert "LAW_API_OC_ALIAS_USED" in cfg.warnings


def test_railway_real_primary_oc_still_wins():
    with _env(
        RAILWAY_PROJECT_ID="project-test",
        LAW_API_OC="registered-primary-oc",
        LAW_API_KEY="registered-legacy-oc",
    ):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "registered-primary-oc"
    assert cfg.law_api_credential_source == "LAW_API_OC"
    assert "LAW_API_OC_PLACEHOLDER_DETECTED_ON_RAILWAY" not in cfg.warnings


def test_railway_placeholder_without_any_fallback_remains_configured():
    with _env(
        RAILWAY_PUBLIC_DOMAIN="example.up.railway.app",
        LAW_API_OC="paradiso",
    ):
        cfg = load_grounding_config()
    assert cfg.law_api_credential == "paradiso"
    assert cfg.law_api_credential_source == "LAW_API_OC"
    assert cfg.law_api_configured is True
    assert "LAW_API_OC_PLACEHOLDER_DETECTED_ON_RAILWAY" in cfg.warnings
