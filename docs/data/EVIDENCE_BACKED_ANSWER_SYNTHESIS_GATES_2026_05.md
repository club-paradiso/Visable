# Evidence-Backed Answer Synthesis Gates (2026-05)

Status: implemented (Parts A–K). Part L (static visa-code search UX, document /
procedure de-duplication, static-answer accuracy gates) is intentionally
deferred to a **follow-up PR** so this change stays reviewable — see
"Deferred: Part L" at the bottom.

## Problem

Recent work built a strong *retrieval / evidence* stack:

* generalized legal-issue extraction (`legal_issue_types`),
* `legal_analysis` (issue taxonomy, practical posture, decisive facts),
* an official-evidence ontology + generalized source-family routing,
* a query planner (`evidence_query_plan`),
* source-panel diagnostics, and a frontend rendering contract.

Despite all of that, production smoke still showed **weak final answers**. The
observed case:

> **Q:** `H-1 외국인등록은 언제 해야 하나요?`
> **A:** too vague; says official confirmation is needed too early; gives no
> strong practical registration/reporting answer; ends by saying it is *not*
> based on verified manual excerpts; model shown as `google/gemma-4-31b-it:free`;
> source diagnostics still show `statute: bad_response`.

The retrieval layer decides *what evidence exists*. Nothing was checking whether
the **final synthesized answer** was actually useful for the detected legal issue
*before it was shown*. A weak live-model answer was rendered unmodified.

## Why this is not a case-by-case patch

We do **not** hardcode H-1 registration, add a special H-1 prompt, invent
citations, pretend direct evidence exists, or hide uncertainty. Instead we add a
reusable, **issue-type** answer-shape contract + a deterministic quality gate +
a deterministic synthesis repair. The same machinery serves H-1, G-1, E-7, F-2,
C-3, … because contracts are keyed by *legal issue type*, never by visa code.

## Pipeline

```
question
 → immigration_facts
 → legal_issue_types
 → proposed_activity_type
 → evidence_query_plan
 → normalized evidence
 → answer_certainty_level
 → answer_shape_contract        (Part A — NEW)
 → answer_quality_gate          (Part B — NEW)
 → final answer (repaired if the live answer fails)  (Part C — NEW)
```

## Part A — Answer shape contracts by legal issue type

`backend/services/answer_shape.py` defines `ANSWER_SHAPE_CONTRACTS`, a registry
of required answer "slots" per issue type, and
`build_answer_shape_contract(...)` which selects exactly one contract from the
detected `legal_issue_types` (most specific issue wins) and prunes
not-applicable slots (e.g. no `target_status` slot when no target was asked).

| Contract key | Selected for issue types | Required slots (summary) |
|---|---|---|
| `registration_or_residence_report` | `registration_or_residence_report`, `reporting_duty` | direct practical answer · trigger event · deadline basis/uncertainty · filing channel · required fact checks · source confidence · official-confirmation questions |
| `activity_scope` | `activity_scope`, `outside_status_activity` | practical risk posture · current status as primary basis · proposed-activity classification · permission/change needed · decisive facts · source confidence |
| `workplace_change_addition` | `workplace_change_addition`, `post_status_change_residual_duty` | current-status role · employer/workplace/client distinction · report-vs-permission distinction · previous-status comparative (only if status changed) · decisive facts · source confidence |
| `status_change_route` | `status_change` | current status · target status · route framing · eligibility without invented documents · required official confirmation · source confidence |
| `documents_needed` | `documents_needed`, `extension` | procedure name · status/procedure target · document list **or** "checklist unavailable + next action" · source confidence |
| `study_on_non_study_status` | `study_on_non_study_status` | current status/purpose · study activity type (degree/credit/non-credit/audit/language) · D-2/D-4 comparison if relevant · permission/status-change risk · decisive facts · source confidence |
| `work_on_non_work_status` | `work_on_non_work_status`, `employment_restriction` | paid/unpaid distinction · current-status allowed scope · comparison status if relevant · risk posture · source confidence |
| `legal_general` | fallback | direct practical answer · source confidence |

Contracts are **issue-type-specific, not visa-code-specific**.

## Part B — Answer quality gate

`evaluate_answer_shape(answer, metadata, answer_shape_contract) -> quality_result`
is fully deterministic and side-effect free. It detects:

* missing direct practical answer / generic-avoidance opening,
* overuse of `확인 필요` / "confirm" without analysis,
* missing current status / activity classification / decisive facts / source confidence,
* forbidden irrelevant terms (e.g. study/`D-2`/`D-4` wording in a registration answer),
* overconfident language when `answer_certainty_level` is not `direct`,
* an answer that says it is *not based on the manual* despite structured/manual context existing,
* a source-limitation note placed on the **first line** (Part G), and
* any missing issue-specific required slots.

Return shape:

```json
{
  "passed": true,
  "warnings": [],
  "missing_slots": [],
  "repair_strategy": "retry_model | deterministic_synthesis | source_limited_note"
}
```

## Part C — Deterministic synthesis fallback for a failed shape

When the **live** model answer fails the contract *structurally*, `/api/ask` no
longer shows the weak answer. `_apply_answer_shape_gate(...)` repairs it with
deterministic synthesis built from `legal_analysis` (practical posture,
immigration facts, issue types, proposed activity, source-family statuses,
certainty), reusing `build_legal_analysis_fallback_answer(..., intro_mode="quality_repair")`.

The synthesizer gained an `intro_mode`:

* `outage` (default, unchanged): provider unavailable → "AI 모델이 일시적으로 …".
* `quality_repair`: the model *did* answer but failed the gate → **lead with the
  practical answer**, no outage notice, no uncertainty-first opening.

The synthesis is natural Korean/English: no internal `snake_case` field names, no
English confirmation questions in a Korean answer, no irrelevant deadline/address
questions outside registration, no bare `확인하세요` as the whole answer, no
invented citations.

## Part F — Model weak-answer guard

`/api/ask` now returns (non-secret) metadata:

* `answer_shape_contract`, `answer_shape_version`
* `answer_quality_gate_passed`, `answer_quality_gate_warnings`, `missing_answer_slots`
* `final_model_quality_warning` — true when `final_model` ≠ the configured primary model
* `answer_shape_failed_by_model`
* `model_answer_repaired_by_deterministic_synthesis`

Model/provider policy is **unchanged**. When a live answer fails the gate we use
deterministic synthesis (the candidate-retry path is reserved and only used by the
existing provider-failure logic) so a weak answer is never displayed unmodified.
`deterministic_fallback_answer_used` stays `false` on a quality repair — it
specifically means "provider unavailable", which is a different state.

## Part G — Source limitation wording

* Simple procedural answers no longer **start** with "cannot verify" when
  structured analysis exists.
* The source limitation is placed **after** the practical answer.
* Registration/reporting answers use the concise wording:
  `현재 연결된 직접 근거는 제한적이므로, 최종 기한과 제출 방식은 1345/HiKorea/관할 관서에서 확인하세요.`
* `본 답변은 공식 매뉴얼에 근거하지 않습니다.` is avoided when manual/legal
  structured context exists (the gate flags it explicitly).

## Regression examples (tests, not special logic)

| Question | Expected generalized behavior |
|---|---|
| `H-1 외국인등록은 언제 해야 하나요?` | `registration_or_residence_report` contract; practical registration/reporting framing; entry/stay-period/deadline/filing-channel fact checks; **no** university/credit/D-2/D-4/course/계절학기; no uncertainty-first opening; honest source confidence. |
| `E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?` | `workplace_change_addition` (residual-duty) contract; current `F-2-99` primary, prior `E-7` comparative; **no** overconfident no-duty conclusion. |
| `G-1-5로 … 대학교에 등록하거나 청강하거나 여름 계절학기를 수강 …` | `study_on_non_study_status`; `G-1-5` sub-status preserved; `D-2/D-4` only as comparison; Korean confirmation questions; no internal field labels. |
| `Can I change status to F-2-99?` (current H-1) | `status_change_route`; current `H-1`, target `F-2-99` (no target loss). |
| `C-3 단기방문으로 paid work를 할 수 있나요?` | `work_on_non_work_status` / `employment_restriction`; `C-3`/`C-4` comparison; **no** invented penalties. |

## Part H — Smoke output

`scripts/smoke_ai_live_quality.py` now reports `answer_shape_contract`,
`answer_quality_gate_passed`, `answer_quality_gate_warnings`,
`missing_answer_slots`, `final_model_quality_warning`,
`model_answer_repaired_by_deterministic_synthesis`, `generic_avoidance_warning`,
`source_limitation_first_line_warning`, and `irrelevant_term_warning`, and warns
when a registration answer lacks deadline/trigger/filing-channel slots, an answer
opens with generic uncertainty, a source limitation precedes the practical
analysis, an H-1 registration answer mentions study terms, a G-1-5 Korean answer
contains English questions or `snake_case`, or an E-7/F-2-99 answer uses
overconfident no-duty language without direct evidence.

## Part I — Tests

`backend/tests/test_evidence_backed_answer_gates.py` covers contract generation
by issue type, the gate catching the weak H-1 registration answer, the gate
passing a useful registration answer, deterministic synthesis repair via
`/api/ask`, source-limitation placement after practical guidance, no irrelevant
study terms in a registration answer, no overconfident language for E-7/F-2-99
limited certainty, the G-1-5 fallback staying Korean and natural, the C-3
paid-work answer inventing no penalties, the response metadata including the
gate fields, and the smoke harness statically recognizing the gate metadata.

## Known limitations

* Direct official evidence may still not exist for every scenario; the gate makes
  the answer **honest and useful**, not a substitute for a verified manual.
* Deterministic synthesis is a structured preparation note, not a full LLM memo.
* Final agency determination (1345 / HiKorea / the competent immigration office)
  remains required.

## Safety note

Nothing here changes OpenRouter / Ollama / law-API credentials or model
selection policy, fabricates citations, or hides uncertainty. The gate is
warn-and-repair, never "approve". All gate logic is deterministic and offline.

## Deferred: Part L (follow-up PR)

The static visa-code **search UX** work — canonical-id / duplicate-public-code
handling (e.g. `D-4-2K`), unifying `절차별 안내` and `구비서류`, hiding
unavailable procedure tabs, procedure-specific fee separation,
`evaluate_visa_result_card_shape`, deterministic render repair, and the static
visa-search smoke — is **not** in this PR. It touches the 17k-line `index.html`
render path and would make this diff too large to review safely. It will land as
a dedicated follow-up so the answer-synthesis gate (Parts A–K) can be reviewed
and merged on its own.
