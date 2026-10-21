"""/api/ask grounds questions without verified knowledge facts in approved manual excerpts.

Waymaker QA 2026-10-16: only D-2 / D-4 / E-7 extension had published knowledge
facts, so every other question (E-7 workplace change, F-6 extension, G-1-5
work, E-9 visa issuance, ...) reached the model with no source and the model
answered from memory (it named a "체류자격 증명서" no manual lists). The approved
2026.9 manuals are in the FTS index; services/manual_evidence.py retrieves
excerpts from it for the prompt, the source panel and the deterministic note.

Covered here (no network; the model is mocked as in the other Waymaker tests):

* E-7 근무처 변경 / F-6 연장 -> stay-manual excerpts with pages.
* E-9 사증발급인정서 -> visa-issuance manual only.
* G-1-5 -> no sibling sub-code excerpts, parent excerpts labelled as such.
* Off-topic -> scoped reply, no excerpts.
* Scope separation never mixes the two manuals, and only approved chunks are used.
* Questions without evidence keep the "not based on the manual" notices.

The index is being rebuilt with Markdown-derived chunks, so assertions are about
scope, page ranges and labels, never about exact excerpt text.

    python3 -m pytest backend/tests/test_waymaker_manual_evidence_grounding.py -q
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402
from services import manual_evidence as me  # noqa: E402
from services import manual_registry as mr  # noqa: E402
from services import manual_search as ms  # noqa: E402

CANDS = ["a/one:free", "b/two:free"]
MODEL_ANSWER = "매뉴얼 발췌를 기준으로 안내합니다. 최종 판단은 1345 또는 하이코리아에서 확인하세요."
STAY_TITLE = "외국인체류 안내매뉴얼"
VISA_TITLE = "사증발급 안내매뉴얼"

E7_WORKPLACE = "E-7 비자로 일하고 있는데 회사를 옮기려고 합니다. 근무처 변경은 어떻게 하나요?"
F6_EXTENSION = "F-6 결혼이민 체류기간 연장하려면 어떻게 해야 하나요?"
E9_CCVI = "E-9 사증발급인정서 신청 서류가 뭔가요?"
G15_WORK = "G-1-5인데 취업할 수 있나요?"
OFF_TOPIC = "오늘 서울 날씨 어때요?"


def _index_has_approved_evidence() -> bool:
    return ms.index_composition().get("directEvidenceChunks", 0) > 0


async def _openrouter_down(prompt, model=None, max_tokens=None, **kwargs):
    raise HTTPException(
        status_code=502,
        detail={"error": "openrouter_upstream_error", "status": 503, "message": "No healthy upstream"},
    )


def _ask(question: str, *, live: bool = True, lang: str = "ko", **payload):
    """POST /api/ask with a mocked model; returns (body, prompts sent to the model)."""
    prompts = []

    async def _answers(prompt, model=None, max_tokens=None, **kwargs):
        prompts.append(prompt)
        return MODEL_ANSWER

    old_mode = os.environ.get("LAW_GROUNDING_MODE")
    os.environ["LAW_GROUNDING_MODE"] = "audit"
    os.environ.pop("LAW_API_OC", None)
    os.environ.pop("LAW_API_KEY", None)
    try:
        pb._reset_visas_cache_for_tests()
        pb._reset_grounding_cache_for_tests()
        pb._reset_openrouter_model_cooldowns_for_tests()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-test-key"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "_call_openrouter", _answers if live else _openrouter_down):
            resp = TestClient(pb.app).post("/api/ask", json={"question": question, "lang": lang, **payload})
        assert resp.status_code == 200, resp.text
        return resp.json(), prompts
    finally:
        pb._reset_openrouter_model_cooldowns_for_tests()
        if old_mode is None:
            os.environ.pop("LAW_GROUNDING_MODE", None)
        else:
            os.environ["LAW_GROUNDING_MODE"] = old_mode


def _pages(body):
    return [int(s["page_range"]) for s in body["manual_evidence_sources"]]


def _cited_titles(prompt: str):
    return set(re.findall(r"「(외국인체류 안내매뉴얼|사증발급 안내매뉴얼) 2026\.9」 p\.\d+", prompt))


@unittest.skipUnless(_index_has_approved_evidence(), "manual search index with approved chunks not present")
class StayProcedureEvidenceTests(unittest.TestCase):
    def test_e7_workplace_change_gets_stay_manual_excerpts_with_pages(self):
        body, prompts = _ask(E7_WORKPLACE)
        self.assertTrue(body["manual_evidence_used"])
        self.assertEqual(body["manual_evidence_status"], me.STATUS_USED)
        self.assertEqual(body["manual_evidence_scopes"], [me.SCOPE_STAY])
        self.assertEqual(body["manual_grounding_status"], "approved_manual_excerpts")
        sources = body["manual_evidence_sources"]
        self.assertTrue(sources)
        for src in sources:
            self.assertEqual(src["manual_scope"], me.SCOPE_STAY)
            self.assertEqual(src["source_title"], STAY_TITLE)
            self.assertEqual(src["source_date"], "2026.9")
            self.assertRegex(src["page_range"], r"^\d+$")
            self.assertEqual(src["procedure_type"], "근무처 변경·추가")
            self.assertFalse(src["reviewed_for_question"])
            self.assertTrue(all(c == "E-7" or c.startswith("E-7-") for c in src["applies_to"]))
        # The 근무처 변경·추가 section of the E-7 chapter (p.221-222 in the 2026.9 PDF).
        self.assertTrue(any(220 <= p <= 223 for p in _pages(body)), _pages(body))

        prompt = prompts[0]
        self.assertIn("[공식 매뉴얼 발췌", prompt)
        self.assertEqual(_cited_titles(prompt), {STAY_TITLE})
        self.assertIn("제출서류, 수수료, 기한, 허가기간, 서식 번호는 아래 발췌에 적힌 것만 쓰십시오.", prompt)
        self.assertIn("Never name a document the excerpts do not name.", prompt)
        self.assertNotIn("이 답변은 공식 출입국·외국인정책본부 매뉴얼에 근거하지 않습니다", prompt)
        # The excerpt rule is restated after the answer-quality contract, so the
        # natural-Korean/style directives cannot override it.
        self.assertGreater(prompt.rfind("[Manual excerpt rule"), prompt.rfind("[Answer quality contract]"))

    def test_verified_grounding_fields_stay_reserved_for_knowledge_facts(self):
        body, _ = _ask(E7_WORKPLACE)
        self.assertFalse(body["grounding_used"])
        self.assertEqual(body["grounding_sources"], [])
        self.assertEqual(body["direct_manual_sources"], [])
        # Retrieved excerpts lift the answer basis to source-limited, never higher.
        self.assertEqual(body["answer_quality_mode"], "source_limited")
        self.assertTrue(body["requires_official_confirmation"])

    def test_f6_extension_gets_the_f6_extension_pages(self):
        body, prompts = _ask(F6_EXTENSION)
        self.assertEqual(body["manual_evidence_scopes"], [me.SCOPE_STAY])
        pages = _pages(body)
        self.assertTrue(any(498 <= p <= 503 for p in pages), pages)
        for src in body["manual_evidence_sources"]:
            self.assertEqual(src["manual_scope"], me.SCOPE_STAY)
            self.assertTrue(all(c.startswith("F-6") for c in src["applies_to"]), src["applies_to"])
        # Sub-code pages are labelled as such for a parent-level question.
        if any(s["applicability"] == "subcode_specific" for s in body["manual_evidence_sources"]):
            self.assertIn("전용 — F-6 전체에 적용되는 규칙으로 쓰지 말 것", prompts[0])

    def test_the_manual_location_lines_are_still_appended(self):
        body, _ = _ask(F6_EXTENSION)
        self.assertIn("공식 매뉴얼 위치", body["answer"])
        self.assertIn("p.498", body["answer"])


@unittest.skipUnless(_index_has_approved_evidence(), "manual search index with approved chunks not present")
class VisaIssuanceEvidenceTests(unittest.TestCase):
    def test_e9_ccvi_reads_the_visa_issuance_manual_only(self):
        body, prompts = _ask(E9_CCVI)
        self.assertEqual(body["manual_evidence_scopes"], [me.SCOPE_VISA])
        self.assertTrue(body["manual_evidence_sources"])
        for src in body["manual_evidence_sources"]:
            self.assertEqual(src["manual_scope"], me.SCOPE_VISA)
            self.assertEqual(src["source_title"], VISA_TITLE)
        self.assertEqual(_cited_titles(prompts[0]), {VISA_TITLE})
        self.assertNotIn("=== 체류 절차 발췌", prompts[0])

    def test_e9_extension_reads_the_stay_manual_only(self):
        body, prompts = _ask("E-9 체류기간 연장 서류는?")
        self.assertEqual(body["manual_evidence_scopes"], [me.SCOPE_STAY])
        self.assertEqual(_cited_titles(prompts[0]), {STAY_TITLE})


@unittest.skipUnless(_index_has_approved_evidence(), "manual search index with approved chunks not present")
class SubcodeEvidenceTests(unittest.TestCase):
    def test_g1_5_gets_no_sibling_subcode_rules_and_labels_parent_rules(self):
        body, prompts = _ask(G15_WORK)
        sources = body["manual_evidence_sources"]
        self.assertTrue(sources)
        self.assertEqual(body["manual_evidence_scopes"], [me.SCOPE_STAY])
        self.assertTrue(any(s["applicability"] == "exact_subcode" for s in sources))
        for src in sources:
            self.assertIn(src["applicability"], {"exact_subcode", "parent", "untagged"})
            self.assertIn(src["applies_to"], (["G-1-5"], ["G-1"], []))
        prompt = prompts[0]
        if any(s["applicability"] == "parent" for s in sources):
            self.assertIn("G-1 공통 기준 — G-1-5에 그대로 적용되는지는 확인 필요", prompt)
        # A G-1 parent rule is never presented as a G-1-5 rule.
        self.assertNotRegex(prompt, r"\[발췌 \d+\][^\n]*적용: G-1(?:, |$)")

    def test_sibling_subcode_chunk_is_dropped(self):
        chunk = {"status_codes": ["G-1-6", "G-1-11"], "body": "인도적 체류허가자(G-1-6) 관련"}
        self.assertEqual(me.applicability(chunk, "G-1", "G-1-5")[0], "sibling_subcode")

    def test_parent_question_labels_subcode_chunks(self):
        chunk = {"status_codes": ["F-6-1"], "body": "국민의 배우자(F-6-1)"}
        self.assertEqual(me.applicability(chunk, "F-6", ""), ("subcode_specific", ["F-6-1"]))
        note = me._applicability_note(
            {"applicability": "subcode_specific", "applies_to": ["F-6-1"]}, "F-6", "")
        self.assertIn("F-6-1 전용", note)

    def test_free_text_subcode_is_used_for_retrieval_only(self):
        self.assertEqual(me.request_codes("G-1-5인데 취업할 수 있나요?", None, None), ("G-1", "G-1-5"))
        self.assertEqual(me.request_codes("F-6-1 연장", "F-6", None), ("F-6", "F-6-1"))
        # A sub-code of another family never overrides the detected status.
        self.assertEqual(me.request_codes("E-7 근무처, 예전엔 D-2-1", "E-7", None), ("E-7", ""))
        body, _ = _ask(G15_WORK)
        # Document routing still never takes a sub-code from free text.
        self.assertFalse(body["grounding_used"])


@unittest.skipUnless(_index_has_approved_evidence(), "manual search index with approved chunks not present")
class ScopeSeparationTests(unittest.TestCase):
    QUESTIONS = (
        (E7_WORKPLACE, "workplace_change", [me.SCOPE_STAY]),
        (F6_EXTENSION, "extension", [me.SCOPE_STAY]),
        ("D-2 유학생인데 시간제취업 허가 받으려면 뭐가 필요해요?", "activities_outside_status", [me.SCOPE_STAY]),
        (E9_CCVI, None, [me.SCOPE_VISA]),
        ("E-9 사증발급인정서 연장은 어떻게 하나요?", "extension", [me.SCOPE_VISA]),
        ("D-2 사증 발급에 필요한 첨부서류는?", None, [me.SCOPE_VISA]),
        ("E-9 사증발급인정서로 입국했는데 체류기간 연장은 어떻게 하나요?", "extension",
         [me.SCOPE_STAY, me.SCOPE_VISA]),
    )

    def test_procedure_scope_is_chosen_by_procedure(self):
        for question, task, expected in self.QUESTIONS:
            with self.subTest(question=question):
                self.assertEqual([s for s, _ in me.procedure_scopes(question, task, has_code=True)], expected)

    def test_no_scope_without_a_procedure_or_status(self):
        self.assertEqual(me.procedure_scopes("H-1 비자인데 계절학기를 수강할 수 있을까요?", None, has_code=True), [])
        self.assertEqual(me.procedure_scopes("HiKorea 방문 예약 전에 뭘 확인해야 하나요?", None, has_code=False), [])

    def test_every_excerpt_comes_from_its_scopes_manual_and_is_approved(self):
        con = sqlite3.connect(f"file:{ms.index_path()}?mode=ro", uri=True)
        try:
            for question, task, _ in self.QUESTIONS:
                code, sub = pb._detect_visa_codes(None, None, question)
                ev = me.retrieve_manual_evidence(question, visa_code=code, visa_sub_code=sub, task_type=task)
                with self.subTest(question=question):
                    self.assertEqual(ev["status"], me.STATUS_USED)
                    self.assertLessEqual(len(ev["excerpts"]), me.MAX_EXCERPTS)
                    self.assertLessEqual(sum(len(e["text"]) for e in ev["excerpts"]), me.MAX_TOTAL_CHARS)
                    for ex in ev["excerpts"]:
                        source_id, state, direct = con.execute(
                            "SELECT source_id, approval_state, direct_evidence FROM chunk WHERE chunk_id = ?",
                            (ex["chunk_id"],),
                        ).fetchone()
                        self.assertEqual((state, direct), ("approved", 1))
                        family = mr.derive_family(source_id)[0]
                        self.assertEqual(family, {me.SCOPE_STAY: "stay_guide_manual",
                                                  me.SCOPE_VISA: "visa_issuance_manual"}[ex["scope"]])
        finally:
            con.close()

    def test_a_two_procedure_question_gets_two_separate_blocks(self):
        question = "E-9 사증발급인정서로 입국했는데 체류기간 연장은 어떻게 하나요?"
        ev = me.retrieve_manual_evidence(question, visa_code="E-9", task_type="extension")
        block = me.prompt_block(ev)
        stay_at = block.find("=== 체류 절차 발췌")
        visa_at = block.find("=== 사증발급 절차 발췌")
        self.assertGreaterEqual(stay_at, 0)
        self.assertGreater(visa_at, stay_at)
        self.assertNotIn(f"「{VISA_TITLE}", block[stay_at:visa_at])
        self.assertNotIn(f"「{STAY_TITLE}", block[visa_at:])

    def test_unapproved_chunks_have_no_body_for_grounding(self):
        con = sqlite3.connect(f"file:{ms.index_path()}?mode=ro", uri=True)
        try:
            unapproved = con.execute(
                "SELECT chunk_id FROM chunk WHERE approval_state != 'approved' LIMIT 1").fetchone()
            approved = con.execute(
                "SELECT c.chunk_id, length(f.body) FROM chunk c JOIN chunk_fts f ON f.rowid = c.chunk_id"
                " WHERE c.approval_state = 'approved' AND c.direct_evidence = 1 AND length(f.body) > 600 LIMIT 1"
            ).fetchone()
        finally:
            con.close()
        if unapproved:
            self.assertEqual(me.chunk_bodies([unapproved[0]]), {})
        bodies = me.chunk_bodies([approved[0]])
        # Full chunk text, not the <=320-char search snippet.
        self.assertEqual(len(bodies[approved[0]]), approved[1])


class MarkdownPreferenceTests(unittest.TestCase):
    """A page with both a PDF row and page-mapped Markdown chunks cites the Markdown text."""

    def test_markdown_chunk_wins_its_page_and_keeps_the_best_score(self):
        ranked = [
            {"source_id": "stay_manual_2026_09_18_pdf", "page": 498, "score": 9.0, "chunk_id": 1},
            {"source_id": "stay_manual_2026_09_18_md", "page": 498, "score": 4.0, "chunk_id": 2},
            {"source_id": "stay_manual_2026_09_18_md", "page": 498, "score": 5.0, "chunk_id": 3},
            {"source_id": "stay_manual_2026_09_18_pdf", "page": 499, "score": 6.0, "chunk_id": 4},
        ]
        picked = me.pick_per_page(ranked)
        self.assertEqual([(c["page"], c["chunk_id"]) for c in picked], [(498, 3), (499, 4)])
        self.assertEqual(picked[0]["score"], 9.0)

    def test_page_zero_chunks_are_never_evidence(self):
        ranked = [{"source_id": "stay_manual_2026_09_18_md", "page": 0, "score": 9.0, "chunk_id": 5}]
        self.assertEqual(me.pick_per_page(ranked), [])

    @unittest.skipUnless(_index_has_approved_evidence(), "manual search index not present")
    def test_live_index_prefers_markdown_where_a_page_has_it(self):
        con = sqlite3.connect(f"file:{ms.index_path()}?mode=ro", uri=True)
        try:
            md_pages = {
                (mr.derive_family(sid)[0], page)
                for sid, page in con.execute(
                    "SELECT source_id, page FROM chunk WHERE source_id LIKE '%\\_md' ESCAPE '\\'"
                    " AND approval_state = 'approved' AND direct_evidence = 1 AND page > 0")
            }
            unapproved_md = {
                cid for (cid,) in con.execute(
                    "SELECT chunk_id FROM chunk WHERE source_id LIKE '%\\_md' ESCAPE '\\'"
                    " AND (approval_state != 'approved' OR direct_evidence = 0 OR page = 0)")
            }
        finally:
            con.close()
        if not md_pages:
            self.skipTest("index has no page-mapped Markdown chunks")
        seen_md = False
        for question, code, task in ((F6_EXTENSION, "F-6", "extension"), (E7_WORKPLACE, "E-7", "workplace_change"),
                                     (E9_CCVI, "E-9", None)):
            ev = me.retrieve_manual_evidence(question, visa_code=code, task_type=task)
            for ex in ev["excerpts"]:
                self.assertNotIn(ex["chunk_id"], unapproved_md)
                self.assertGreater(ex["page"], 0)
                family = mr.derive_family(ex["source_id"])[0]
                if (family, ex["page"]) in md_pages:
                    seen_md = True
                    self.assertEqual(ex["text_kind"], "markdown", (question, ex["page"]))
                # The citation is the edition + the chunk's PDF page either way.
                self.assertTrue(ex["citation"].endswith(f"2026.9」 p.{ex['page']}"))
        self.assertTrue(seen_md)


@unittest.skipUnless(_index_has_approved_evidence(), "manual search index with approved chunks not present")
class DeterministicNoteTests(unittest.TestCase):
    def test_fallback_note_shows_the_excerpts_and_pages(self):
        body, _ = _ask(F6_EXTENSION, live=False)
        answer = body["answer"]
        self.assertTrue(body["deterministic_fallback_answer_used"])
        self.assertIn("공식 매뉴얼 발췌", answer)
        self.assertRegex(answer, r"「외국인체류 안내매뉴얼 2026\.9」 p\.(49[89]|50[0-3])")
        self.assertIn("사람이 검토한 목록은 아닙니다", answer)
        # Uncertainty notices stay.
        self.assertIn("이 메모는 최종 판단이 아니며", answer)
        self.assertNotIn(VISA_TITLE, answer)

    def test_fallback_note_for_visa_issuance_cites_the_visa_manual(self):
        body, _ = _ask(E9_CCVI, live=False)
        self.assertIn(f"「{VISA_TITLE} 2026.9」 p.", body["answer"])
        self.assertNotIn(f"「{STAY_TITLE} 2026.9」 p.", body["answer"])

    def test_note_snippet_never_quotes_a_phrase_the_confidence_gate_rewrites(self):
        lines = me.note_lines([{
            "citation": "「외국인체류 안내매뉴얼 2026.9」 p.10", "page_range": "10",
            "applies_to": ["D-2"], "excerpt": "유학생의 시간제취업은 허가를 받은 경우 주당 일정 시간 근무가 가능합니다. 다만",
        }], is_ko=True)
        self.assertNotIn("가능합니다", "\n".join(lines))
        self.assertIn("p.10 [D-2]: 유학생의 시간제취업은", lines[1])


class OffTopicAndNoEvidenceTests(unittest.TestCase):
    def test_off_topic_fallback_is_a_scoped_reply_without_excerpts(self):
        body, _ = _ask(OFF_TOPIC, live=False)
        self.assertEqual(body["fallback_answer_kind"], "out_of_scope_notice")
        self.assertIn("한국 체류·비자 관련 질문을 안내합니다", body["answer"])
        self.assertNotIn("공식 매뉴얼 발췌", body["answer"])
        self.assertNotIn("확인할 사실", body["answer"])
        self.assertEqual(body["manual_evidence_status"], me.STATUS_NOT_ATTEMPTED)
        self.assertEqual(body["manual_evidence_sources"], [])

    def test_off_topic_model_prompt_has_no_excerpts(self):
        body, prompts = _ask(OFF_TOPIC)
        self.assertNotIn("[공식 매뉴얼 발췌", prompts[0])
        self.assertFalse(body["manual_evidence_used"])

    def test_question_without_evidence_keeps_the_not_from_manual_notice(self):
        body, prompts = _ask("H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?", visa_code="H-1")
        self.assertEqual(body["manual_evidence_status"], me.STATUS_NOT_ATTEMPTED)
        self.assertEqual(body["manual_grounding_status"], "absent")
        self.assertIn("이 답변은 공식 출입국·외국인정책본부 매뉴얼에 근거하지 않습니다", prompts[0])
        self.assertIn("Specific manual document guidance was NOT found", prompts[0])

    def test_verified_grounding_is_not_mixed_with_retrieved_excerpts(self):
        body, prompts = _ask("D-2 유학 비자 체류기간 연장할 때 필요한 서류 알려주세요.")
        self.assertTrue(body["grounding_used"])
        self.assertEqual(body["manual_evidence_status"], "not_needed")
        self.assertEqual(body["manual_evidence_sources"], [])
        self.assertNotIn("[공식 매뉴얼 발췌", prompts[0])

    def test_missing_index_degrades_to_an_explicit_status(self):
        with patch.dict(os.environ, {"MANUAL_SEARCH_INDEX_PATH": str(REPO_ROOT / "no-such-index.sqlite3")}):
            body, prompts = _ask(E7_WORKPLACE)
        self.assertEqual(body["manual_evidence_status"], me.STATUS_INDEX_UNAVAILABLE)
        self.assertFalse(body["manual_evidence_used"])
        self.assertEqual(body["manual_grounding_status"], "absent")
        self.assertIn("이 답변은 공식 출입국·외국인정책본부 매뉴얼에 근거하지 않습니다", prompts[0])


class FrontendRenderingContractTests(unittest.TestCase):
    """ai.html renders manual_evidence_sources in the source panel."""

    def setUp(self):
        self.html = (REPO_ROOT / "ai.html").read_text(encoding="utf-8")

    def test_source_panel_renders_the_excerpt_row(self):
        self.assertIn("manual_evidence_sources: asArray(m.manual_evidence_sources)", self.html)
        self.assertIn('data-row-kind="manual-excerpts"', self.html)
        self.assertIn("이 질문에 맞춰 사람이 검토한 목록은 아니므로", self.html)

    def test_excerpts_count_as_official_grounding_for_the_unavailable_warning(self):
        self.assertIn("|| manualSources.length > 0 || excerptSources.length > 0", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
