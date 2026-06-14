"""Deterministic frontend coverage for the Waymaker answer-state polish.

The Waymaker answer surface already distinguishes several states (evidence-grounded
answer, deterministic fallback, evidence unverified, provider timeout). This guards
one scoped polish: the deterministic-fallback note on the 200 path is rendered as a
clear status callout — matching the prominence the same state gets on the 503 path —
instead of a faint footnote, so users can tell a temporary preparation note apart
from an evidence-grounded model answer. It also pins the surrounding state handling
so the polish does not regress the other states.

Static text checks against index.html (no browser); localized copy is asserted
against the external locale packs.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import SUPPORTED_LOCALES, load_packs  # noqa: E402


class WaymakerAnswerStatePolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        start = cls.html.find("async function submitAiAnalysis")
        assert start != -1, "submitAiAnalysis not found in index.html"
        nxt = cls.html.find("\nasync function ", start + 1)
        nxt2 = cls.html.find("\nfunction ", start + 1)
        end = min(x for x in (nxt, nxt2) if x != -1)
        cls.submit = cls.html[start:end]
        cls.packs = load_packs()

    def test_deterministic_fallback_renders_clear_callout(self):
        # The deterministic-fallback branch is a visible status callout, not a faint
        # footnote, and is gated on the backend's deterministic_fallback flag.
        self.assertIn("result.deterministic_fallback_answer_used", self.submit)
        self.assertIn("ai-fallback-callout", self.submit)
        self.assertIn('role="status"', self.submit)

    def test_deterministic_fallback_uses_existing_localized_keys(self):
        # Reuses existing keys (no new keys / no parity change required).
        self.assertIn("tx('aiProviderTemporarilyUnavailable')", self.submit)
        self.assertIn("tx('aiFallbackFromMetadata')", self.submit)

    def test_callout_is_theme_aware_not_hardcoded_palette(self):
        # The callout tints via theme variables (with safe fallbacks), so it works
        # under the civic/kitsch themes rather than a fixed colour.
        callout = self.submit.split("ai-fallback-callout", 1)[1].split("</div>", 1)[0]
        self.assertIn("var(--color-warning", callout)
        self.assertIn("var(--t1)", callout)

    def test_other_answer_states_remain_wired(self):
        # Regression guard: the polish must not drop the other Waymaker states.
        self.assertIn("buildProviderErrorHtml(detail)", self.submit)   # 503 provider state
        self.assertIn("response.status === 503", self.submit)
        self.assertIn("tx('aiTimeout')", self.submit)                  # finite-timeout state
        self.assertIn("renderGroundingSourcePanel(result)", self.submit)  # evidence panel
        self.assertIn("result.model_fallback_used", self.submit)       # model-candidate fallback

    def test_reused_keys_have_locale_parity(self):
        for key in ("aiProviderTemporarilyUnavailable", "aiFallbackFromMetadata"):
            for locale in SUPPORTED_LOCALES:
                self.assertIn(key, self.packs[locale], f"{key} missing from {locale} pack")


if __name__ == "__main__":
    unittest.main()
