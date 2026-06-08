# Paradiso AI Answer Grounding Audit — 2026-06

End-to-end audit of the AI search answer / retrieval / grounding pipeline, the
improvements made in branch `claude/paradiso-grounding-audit-1odwB`, and the
remaining limitations. Scope: make nuanced scenario answers source-grounded,
authority-aware, uncertainty-aware, and practically useful — without inventing
legal rules, fabricating citations, weakening disclaimers, or making Paradiso
issue final legal determinations.

The triggering example:

> "G-1-5로 체류중인데 제주대학교에서 수업 청강이 가능할까?"

was too vague — broad caution + "ask 1345" — because the answer did not
separate (a) directly-confirmed official rules, (b) general rules, (c)
practical inference, (d) source gaps, and (e) final-agency confirmation needs.
This is a system-level issue, addressed across retrieval, grounding assembly,
authority hierarchy, answer prompting, and regression QA.

---

## A. Current system diagnosis

### A.1 Pipeline map

```
POST /api/ask  (backend/paradiso_backend.py:3398 `ask`)
  → visa-code + sub-code detection        (_detect_visa_codes, paradiso_backend.py:2274)
  → task-type + risk detection            (_detect_task_type / _risk_level_for_task)
  → manual grounding selection            (_select_grounding → _build_grounded_prompt, :2518)
      else Korea-scoped ungrounded prompt  (_build_ungrounded_korea_scoped_prompt, :3065)
  → visa_data.json / structured-req blocks (_build_visa_data_context_block, :2599)
  → law-grounding intent + (optional) call (services/law_grounding.py)
  → immigration fact extraction            (services/legal_analysis.extract_immigration_facts)
  → activity / legal-issue classification  (legal_analysis.classify_activity_types / classify_legal_issue_types)
  → source-family routing + query plan     (services/evidence_ontology.route_source_families / plan_evidence_queries)
  → official-source retrieval (when wired) (services/law_tools.retrieve_planned_official_sources)
  → evidence normalization + scoring       (law_tools._normalize_candidate, legal_analysis.score_evidence_relevance)
  → structured evidence pack               (law_tools.build_law_evidence_pack)
  → legal analysis object                  (legal_analysis.build_legal_analysis)
  → answer-quality contract + directives   (services/answer_quality.classify_answer_quality / build_answer_directives)
  → answer-shape contract                  (services/answer_shape.build_answer_shape_contract)
  → LLM call (OpenRouter → Groq → Ollama → deterministic fallback)
  → confidence gate + answer-shape gate    (_confidence_gate_answer_text, _apply_answer_shape_gate)
  → source-panel metadata                  (_derive_source_panel_metadata)
```

### A.2 Files inspected

- `backend/paradiso_backend.py` — `/api/ask` entry, prompt assembly, gates, response metadata.
- `backend/services/legal_analysis.py` — fact extraction, activity/issue classification, relevance scoring, `build_legal_analysis`.
- `backend/services/evidence_ontology.py` — ontology dimensions, source-family routing, query planning.
- `backend/services/law_tools.py` — retrieval orchestration, `_normalize_candidate`, `build_law_evidence_pack`.
- `backend/services/answer_quality.py` — answer-quality mode + `build_answer_directives`.
- `backend/services/answer_shape.py` — issue-type answer-shape contracts + gate.
- `backend/services/source_grounding.py`, `citation_verifier.py`, `precedent_sources.py`, `korean_law_client.py`, `law_grounding.py`.
- Eval/QA: `backend/data/eval/*.json`, `scripts/evaluate_paradiso_ai_golden_questions.py`, `backend/tests/*`.
- Frontend: `ai.html` (source-panel rendering references).

### A.3 Source families — wired vs missing

| Authority level | Source family | Status |
| --- | --- | --- |
| 1 Statute | `statute` / `law` | **Wired** (Korean Law OpenAPI, gated by `LAW_GROUNDING_MODE`) |
| 2 Enforcement decree/rule | `enforcement_decree`, `enforcement_rule`, `administrative_rule` | **Wired** |
| 3 MOJ / HiKorea manual | `manual` (외국인체류 안내매뉴얼 grounding bundles + structured requirements) | **Wired (deterministic fixtures)** |
| 4 Notices / forms / glossary | `legal_term` wired; HiKorea notices catalog exists as data | **Partial** — notice catalog present (`data/sources/immigration_notice_sources.json`), not yet fused into `/api/ask` evidence |
| 5 Case law / adjudication | `precedent`, `administrative_appeal`, `constitutional_decision`, `legal_interpretation` | **Scaffold only** — `precedent_sources.py` is list-search scaffold, deliberately NOT wired into the answer path; reported as `planned_not_wired`, never faked |
| 6 Paradiso internal | `visa_data.json`, `doc_master.json`, scenario variants | **Wired** (supplemental context only) |
| 7 LLM inference | — | Explicitly labeled non-source in prompt |

Law/statute grounding: present and safe-by-default (`LAW_GROUNDING_MODE=disabled`
unless an operator enables `audit`/`enabled`). Case-law grounding: **scaffold
only**, correctly surfaced as unavailable rather than fabricated.

### A.4 Weaknesses found (pre-change)

- **Schema gap.** Normalized evidence carried `source_type`, `title`, `summary`,
  `relevance`, dates — but no explicit integer `authority_level`, no public
  `directness` label (DIRECT/PARTIAL/GENERAL/ANALOGICAL/NOT_FOUND), no
  `relevance_reason`, no unified `source_id`/`page_or_section`. Authority was
  implicit in source-family ordering only.
- **Concept-map gaps.** `일반연수`, `원격근무`, `가족초청`, `동성 배우자` were
  unrecognized; `특강` (special lecture) was not treated as study-adjacent; a
  pure concept question ("체류자격외활동허가가 필요한 경우는?") fell through to a
  non-immigration classification; pure volunteer/unpaid-internship activity was
  classified as non-immigration rather than activity-scope.
- **Prompt gap.** The directive layer covered short-answer / official-vs-
  inference separation / disclaimers well, but did not explicitly require, for
  ambiguous not-directly-confirmed scenarios, a concrete **risk-variant
  breakdown** and a **single key dividing line** with institution-specific
  copy-ready scripts.
- **QA gap.** None of the 17 nuanced scenario queries in the task were covered
  by any test or golden fixture.
- **Frontend gap.** The source panel renders `legal_analysis`,
  `source_confidence_level`, and `public_official_sources` but not per-item
  directness/authority badges.

### A.5 Answer-quality failure modes (the "too vague" symptom)

1. Generic caution without separating confirmed vs. inferred.
2. "Ask 1345/HiKorea" endings without the exact questions to ask.
3. No scenario-variant risk classification for genuinely ambiguous cases.
4. No explicit "the official sources do not directly cover this exact case" line
   distinct from the practical answer.

---

## B. Changes made (this branch)

Minimal, additive, architecture-preserving. No `visa_data.json` or
`doc_master.json` edits. No production data churn. No UI redesign.

### B.1 Schema / types — structured evidence model (Stage 2)

`backend/services/evidence_ontology.py` (new, additive):

- **Authority hierarchy** `_AUTHORITY_LEVEL_BY_SOURCE_TYPE` + `AUTHORITY_LEVEL_LABELS`
  implementing levels 1–7 (statute → enforcement decree/rule → manual/HiKorea →
  notice/form/glossary → case law/adjudication → Paradiso internal → LLM
  inference). Unknown types default to 6 so a mislabeled item can never be
  over-ranked as binding authority.
- **Public directness** `PUBLIC_DIRECTNESS_BY_RELEVANCE` mapping internal
  relevance (`direct/related/background/analogical/not_relevant`) to public
  `DIRECT/PARTIAL/GENERAL/ANALOGICAL/NOT_FOUND`. Unknown degrades to `NOT_FOUND`.
- **`to_grounding_item(...)`** projects any internal evidence dict onto the
  compact public schema:
  `{source_id, source_title, source_type, version_or_date, authority_level,
  excerpt, page_or_section, url, directness, relevance_reason}`. It preserves
  real fields and never fabricates — missing values stay empty.
- Helpers `authority_level_for`, `public_source_type_for`, `public_directness_for`.

`backend/services/legal_analysis.py`:

- `build_legal_analysis` now emits a `grounding_items` list (strongest-first,
  NOT_FOUND excluded, capped at 12) built via `to_grounding_item`, with a
  templated `relevance_reason` per directness that states the *relationship* to
  the question (never a legal conclusion).
- `_authority_stub` now carries `authority_level` and `directness`.

`backend/services/law_tools.py`:

- `build_law_evidence_pack` surfaces `grounding_items` at the pack top level
  (also available inside `legal_analysis`). No removed fields → runtime-safe.

### B.2 Retrieval / grounding (Stage 3 — concept coverage)

`backend/services/legal_analysis.py`:

- `classify_activity_types`: added recognition for `일반연수`/general training
  (→ `formal_enrollment`), `원격근무`/`재택근무`/remote work (→ `paid_work`),
  `가족초청`/`동성 배우자`/same-sex spouse (→ `family_or_marriage_related`), and
  `특강`/`세미나`/special lecture (→ `non_credit_audit`).
- `_has_work` extended with remote-work phrasing.
- `classify_legal_issue_types`: a pure concept question mentioning
  `체류자격외활동`/`자격외활동` now classifies as `activity_scope` +
  `outside_status_activity` even with no code/activity; volunteer and unpaid-
  internship activities now classify as `activity_scope` (an activity-scope
  question, not a non-immigration matter).

These are generalized by signal, not by visa code (no hard-coded G-1-5 path).

### B.3 Prompt / template (Stage 4)

`backend/services/answer_quality.py` — `build_answer_directives`:

- For ambiguous scenario questions (`activity_on_status` / `special_situation`)
  whose exact case is **not** directly source-confirmed (`source_assisted` /
  `source_limited` / `source_unavailable`), inject an explicit requirement to:
  split the scenario into 2–4 concrete variants; assign each a plain risk level
  (low / medium / high / not enough information) with the driving factor; state
  the single key dividing line; provide two short copy-ready Korean inquiry
  scripts (institution + 1345/HiKorea) naming exactly what to ask; and end with
  a source-confidence line. This maps directly to answer sections E (risk
  variants), F (dividing line), H (inquiry scripts), I (source confidence).
- Existing disclaimer / no-fake-citation / no-overconfidence posture is
  unchanged and still enforced.

### B.4 Tests / fixtures / QA (Stage 6)

- `backend/data/eval/scenario_grounding_audit_cases_2026_06.json` — all 17
  required scenario queries with tolerant any-of expectations.
- `backend/tests/test_scenario_grounding_audit_2026_06.py` — deterministic
  regression: scenario classification, no-fall-through-to-non-immigration,
  grounding-item schema/authority/directness invariants, and ambiguous-scenario
  directive presence (without weakening disclaimers).
- `docs/qa/AI_SCENARIO_ANSWER_QA_CHECKLIST_2026_06.md` — manual QA checklist for
  live LLM answers (the automated tests cover deterministic structure only).

### B.5 Frontend / source display (Stage 5)

No frontend code changed (single-file 159KB `ai.html`; a per-item card renderer
would be a non-trivial redesign). The backend now exposes everything the panel
needs. **Recommended minimal UI wiring** (documented, not implemented):

- Read `legal_analysis.grounding_items` (already delivered inside the
  `legal_analysis` object the panel consumes) and render, per item: a
  source-type chip, an authority-level badge (1–7 with `AUTHORITY_LEVEL_LABELS`),
  a directness badge (DIRECT/PARTIAL/GENERAL/ANALOGICAL/NOT_FOUND), the
  `version_or_date`, a truncated `excerpt`, and a link when `url` is present.
- Show the overall `source_confidence_level` and an "official source vs.
  inference" indicator derived from the max authority level present.

---

## C. Test results

Commands (from repo root unless noted):

```
cd backend && python3 -m pytest tests/ -q
python3 scripts/evaluate_paradiso_ai_golden_questions.py --strict
cd backend && python3 -m pytest tests/test_scenario_grounding_audit_2026_06.py -v
```

Results:

- New regression suite `test_scenario_grounding_audit_2026_06.py`: **pass**
  (13 tests, 32 subtests).
- Golden-question evaluator (`--strict`): **All regression checks passed.**
- Full backend suite: **1058 passed, 7 failed.** The 7 failures are
  **pre-existing on the branch** and unrelated to this work — all in
  `test_reentry_procedure_coverage.py` / `test_scenario_procedure_variants.py`
  reentry/population checks that read `visa_data.json` scenario records.
  Confirmed pre-existing by re-running with these changes stashed. Not fixed
  here because the constraint forbids modifying `visa_data.json` without
  separate justification, and the failures are a data-coverage matter outside
  this audit's scope.

---

## D. Before / after examples

> The "after" text below illustrates the *target* answer shape now enforced by
> the directive + answer-shape layers for the live model. The deterministic
> tests assert the structural routing/grounding that makes these shapes
> reachable; exact LLM prose is validated via the manual QA checklist.

### D.1 G-1-5 제주대학교 청강

**Before:** "G-1-5는 학업을 위한 자격이 아닙니다 … 위험할 수 있으니 1345/HiKorea에
문의하세요." Broad caution, no separation of confirmed vs. inferred, no variants.

**After (target shape):**
> 공식 자료만으로는 G-1-5 체류자의 '비학점 청강'을 곧바로 허용 또는 금지한다고
> 단정하기 어렵습니다. 다만 학점, 성적표, 수료증, 공식 등록, 장기 수강이 포함되면
> 단순 청강이 아니라 학업/연수 활동으로 보일 수 있어 D-2/D-4 또는 체류자격외활동
> 문제를 확인해야 합니다. 교수 허락을 받아 몇 차례 비공식적으로 참관하는 수준이라면
> 상대적으로 위험은 낮지만, 대학 내부 규정과 출입국 해석은 별도로 확인해야 합니다.
>
> 위험 구분: 비공식 비학점 참관 = 상대적으로 낮음(공식 확인 안 됨) · 대학의 공식
> 청강 등록 = 중간 · 유료 평생교육/어학 수강 = 중간/높음 · 학점·성적표 발생 강의 =
> 높음 · 장기/풀타임 수강 패턴 = 높음.
> 핵심 구분선: 비공식 참관인지, 대학이 공식 교육/등록 활동으로 처리하는지.
> (대학 문의 스크립트 + 1345 문의 스크립트 + 근거 신뢰도 표기 포함.)

Routing verified: `current=G-1-5`, activity `non_credit_audit`, issue
`study_on_non_study_status`, contract `study_on_non_study_status`.

### D.2 D-10 무급 인턴십

**Before:** generic "취업활동은 제한됩니다" without distinguishing unpaid vs paid.

**After (target shape):** practical posture first; classifies `unpaid_internship`
as an **activity-scope** question (not a non-immigration matter); separates "what
official sources confirm" from inference; risk variants by paid/unpaid and by
whether the host treats it as employment; key dividing line = compensation /
employment substance; inquiry scripts for the host org and 1345.

Routing verified: `current=D-10`, activity `unpaid_internship`, issue includes
`activity_scope`.

### D.3 체류자격외활동허가 필요 여부

**Before:** fell through to a non-immigration classification → generic answer.

**After:** classifies as `activity_scope` + `outside_status_activity` even with
no code; answer explains *when* permission is generally required vs. when a
status change is the right route, separating general rule from the user's
specific (unknown) facts, ending with the exact facts to confirm.

Routing verified: issues `["activity_scope", "outside_status_activity"]`,
contract `activity_scope`.

### D.4 F-4 동성 배우자 초청 (difficult family/status scenario)

**Before:** `동성 배우자` unrecognized; generic spouse-sponsorship answer.

**After:** `family_or_marriage_related` activity now detected; classified under
`nationality_or_refugee_context`/family framing; answer must separate what
official sources directly confirm about F-6/family routes from the legal-status
question the sources may not directly address for a same-sex spouse, mark
inference as inference, and give concrete confirmation questions for 1345/the
competent office — without inventing a legal determination.

Routing verified: `current=F-4`, activity `family_or_marriage_related`.

---

## E. Remaining limitations

- **Case law not retrieved.** `precedent_sources.py` is a list-search scaffold;
  court precedent / administrative-appeal / constitutional-decision families are
  reported as `planned_not_wired` and never fabricated. The authority hierarchy
  reserves level 5 and `to_grounding_item` already supports a `case_law` public
  type, so wiring a future precedent adapter requires no schema change.
- **HiKorea notices not fused.** A notice catalog exists as data but is not yet
  merged into `/api/ask` evidence (authority level 4). Tracked as a follow-up.
- **Law grounding is gated.** Statute/decree retrieval only runs when
  `LAW_GROUNDING_MODE` is `audit`/`enabled` (safe-by-default disabled). With it
  disabled, level 1–2 evidence is unavailable and answers correctly degrade to
  inference-aware, source-limited framing.
- **Frontend per-item directness/authority badges** not yet rendered (B.5).
- **Pre-existing reentry/procedure-variant data-coverage test failures** (7)
  remain, by constraint (no `visa_data.json` edits here).
- **Some scenarios still need agency confirmation by design** — every ambiguous
  answer ends with the explicit facts/questions to confirm with 1345 / HiKorea /
  the competent immigration office.

---

## F. Safety statement

- **No final legal determinations.** The confidence gate + directive layer
  forbid unsupported yes/no and certainty wording when `answer_certainty_level`
  is not `direct`; every ambiguous answer routes to risk-variant framing and
  agency-confirmation questions.
- **Uncertainty is marked as uncertain.** Directness defaults to `NOT_FOUND` and
  authority to level 6 for under-described items; the "not directly confirmed"
  separation and source-confidence line are required.
- **No fake official source was added.** No statute/manual/case-law text was
  invented; case law remains an honest scaffold; no citations were fabricated;
  disclaimers were preserved, not weakened; `visa_data.json` / `doc_master.json`
  were not modified.
