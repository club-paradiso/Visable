"""Manual locator in the deterministic preparation note.

When every model fails and the knowledge layer has no verified document facts
(F-6 / F-4 / H-1 extension), the note must point at the exact stay-manual
section and page from the existing 2026.9 status guidance — labelled as not yet
reviewed line by line, never restating requirements, never flattening sub-codes.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402
from services import manual_locator as ml  # noqa: E402

DATA = json.loads(ml.STATUS_GUIDANCE_PATH.read_text(encoding="utf-8"))
REVIEW_LABEL_KO = "사람이 한 줄씩 대조 검토하기 전 원문 기준"


def _guidance(target_prefix: str, procedure: str):
    return [g for g in DATA["guidance"]
            if g.get("procedure") == procedure and str(g.get("target", "")).startswith(target_prefix)]


class LocateTests(unittest.TestCase):
    def test_parent_lists_each_subcode_under_its_own_label(self):
        found = ml.locate("F-6", None, "extension")
        self.assertIsNotNone(found)
        self.assertTrue(found["needs_subcode"])
        expected = sorted((g["target"], g["source"]["pdf_page"]) for g in _guidance("F-6", "extension"))
        self.assertEqual(sorted((e["target"], e["page"]) for e in found["entries"]), expected)
        self.assertEqual({e["target"] for e in found["entries"]}, {"F-6-1", "F-6-2", "F-6-3"})
        self.assertEqual(found["source"]["title_ko"], "외국인체류 안내매뉴얼")

    def test_subcode_never_inherits_a_sibling_entry(self):
        found = ml.locate("F-6", "F-6-1", "extension")
        self.assertEqual({e["target"] for e in found["entries"]}, {"F-6-1"})
        self.assertFalse(found["needs_subcode"])

    def test_unstructured_procedure_uses_the_code_index_page(self):
        self.assertEqual(_guidance("F-4", "extension"), [])
        found = ml.locate("F-4", None, "extension")
        page = DATA["codes"]["F-4"]["procedures"]["extension"]["p"]
        self.assertEqual(found["entries"], [{"target": "F-4", "section": "", "page": page}])

    def test_single_entry_status(self):
        found = ml.locate("H-1", None, "extension")
        (entry,) = found["entries"]
        self.assertEqual(entry["page"], _guidance("H-1", "extension")[0]["source"]["pdf_page"])

    def test_no_locator_without_a_mapped_stay_procedure_or_known_code(self):
        self.assertIsNone(ml.locate("F-6", None, "marriage_divorce_status_change"))
        self.assertIsNone(ml.locate("F-6", None, None))
        self.assertIsNone(ml.locate("ZZ-9", None, "extension"))
        self.assertIsNone(ml.locate("F-6", "E-7-1", "extension"))

    def test_not_applicable_procedures_are_skipped(self):
        checked = 0
        for code, rec in DATA["codes"].items():
            for task, procedure in ml.TASK_PROCEDURE.items():
                state = ((rec.get("procedures") or {}).get(procedure) or {}).get("s")
                if state == "NOT_APPLICABLE" and rec.get("kind") == "status" and not _guidance(code, procedure):
                    self.assertIsNone(ml.locate(code, None, task), (code, procedure))
                    checked += 1
        self.assertGreater(checked, 0)

    def test_only_stay_manual_sources(self):
        # Re-label the stay manual as a visa-domain source: nothing may be located
        # for a stay procedure any more (visa material never answers stay questions).
        relabelled = json.loads(json.dumps(DATA))
        for src in relabelled["sources"].values():
            src["domain"] = "visa"
        with patch.object(ml, "_bundle", lambda: relabelled):
            self.assertIsNone(ml.locate("F-6", None, "extension"))
            self.assertIsNone(ml.locate("F-4", None, "extension"))

    def test_note_lines_label_the_review_state_and_restate_no_requirement(self):
        ko = ml.note_lines("H-1", None, "extension", is_ko=True)
        self.assertIn(REVIEW_LABEL_KO, ko[0])
        summary = _guidance("H-1", "extension")[0]["summary_ko"]
        self.assertNotIn(summary, "\n".join(ko))
        en = ml.note_lines("F-6", None, "extension", is_ko=False)
        self.assertIn("not yet reviewed line by line", en[0])
        self.assertTrue(any("sub-status" in line for line in en))
        self.assertEqual(ml.note_lines("F-6", None, "marriage_divorce_status_change", is_ko=True), [])


def _rate_limited(model):
    return HTTPException(status_code=502, detail={
        "error": "openrouter_http_error", "status": 429, "message": "Rate limit exceeded: free-models-per-min.",
    })


class PreparationNoteTests(unittest.TestCase):
    def setUp(self):
        pb._reset_openrouter_model_cooldowns_for_tests()

    def tearDown(self):
        pb._reset_openrouter_model_cooldowns_for_tests()

    def _ask(self, question):
        async def fail(prompt, model=None, max_tokens=None, **kw):
            raise _rate_limited(model)

        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "_call_openrouter", fail):
            resp = TestClient(pb.app).post("/api/ask", json={
                "question": question, "answer_mode": "fast", "lang": "ko", "stream": False, "consent": True,
            })
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def test_f6_extension_note_points_at_each_subcode_section(self):
        body = self._ask("F-6 체류기간 연장 서류")
        self.assertTrue(body["deterministic_fallback_answer_used"])
        answer = body["answer"]
        self.assertIn("공식 매뉴얼 위치", answer)
        self.assertIn(REVIEW_LABEL_KO, answer)
        for g in _guidance("F-6", "extension"):
            self.assertIn(f"* {g['target']}: p.{g['source']['pdf_page']}", answer)
        self.assertIn("본인 세부자격에 해당하는 항목만", answer)
        # The note's closing caveat stays last.
        self.assertTrue(answer.rstrip().endswith("확인하세요."))

    def test_f4_extension_note_points_at_the_unstructured_page(self):
        answer = self._ask("F-4 연장 서류")["answer"]
        page = DATA["codes"]["F-4"]["procedures"]["extension"]["p"]
        self.assertIn(f"* F-4: p.{page} (구조화 전 원문)", answer)

    def test_verified_structured_answer_is_unchanged(self):
        body = self._ask("D-2 연장시 필수 서류")
        self.assertIsInstance(body.get("structured_answer"), dict)
        self.assertNotIn("공식 매뉴얼 위치", body["answer"])


if __name__ == "__main__":
    unittest.main()
