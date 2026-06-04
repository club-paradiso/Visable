"""Fixture-based parser/normalizer taxonomy tests (Part A / Part B).

These exercise the law_tools parser against synthetic, sanitized sample bodies
that mirror Open Law API shapes (see backend/tests/fixtures/law_api_shapes/).
No live API, no credentials, no real response bodies are involved.

    python3 -m pytest backend/tests/test_law_api_shape_fixtures.py -q
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import law_tools as lt  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "law_api_shapes"


class LawApiShapeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((FIXTURE_DIR / "expected.json").read_text(encoding="utf-8"))

    def test_every_fixture_maps_to_expected_status(self):
        for name, exp in self.expected.items():
            body = (FIXTURE_DIR / name).read_text(encoding="utf-8")
            parsed = lt.parse_law_search_response(body, source_type=exp.get("source_type", "law"))
            with self.subTest(fixture=name):
                self.assertEqual(parsed["error_type"], exp["error_type"], f"{name}: error_type")
                self.assertEqual(parsed["response_shape_hint"], exp["response_shape_hint"], f"{name}: shape")
                if "parser_status" in exp:
                    self.assertEqual(parsed["parser_status"], exp["parser_status"], f"{name}: parser_status")
                self.assertGreaterEqual(len(parsed["results"]), exp.get("min_results", 0), f"{name}: result count")
                # No fixture body should ever be echoed verbatim into the result.
                if exp["response_shape_hint"] in {"html", "xml"}:
                    self.assertNotIn("service page", json.dumps(parsed, ensure_ascii=False))
                    self.assertNotIn("invalid request", json.dumps(parsed, ensure_ascii=False))

    def test_no_shape_collapses_into_bad_response_incorrectly(self):
        # Only the HTML service page is a genuine bad_response; empty / official
        # error / parseable shapes must NOT collapse into LAW_API_BAD_RESPONSE.
        bad = []
        for name, exp in self.expected.items():
            body = (FIXTURE_DIR / name).read_text(encoding="utf-8")
            parsed = lt.parse_law_search_response(body, source_type=exp.get("source_type", "law"))
            if parsed["error_type"] == lt.LAW_API_BAD_RESPONSE and exp["error_type"] != lt.LAW_API_BAD_RESPONSE:
                bad.append(name)
        self.assertEqual(bad, [], f"shapes wrongly collapsed to bad_response: {bad}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
