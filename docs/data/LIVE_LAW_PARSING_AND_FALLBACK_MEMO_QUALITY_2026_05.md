# Live Law Parsing & Fallback Memo Quality (2026-05)

Repair of live Open Law API response parsing/normalization and of the
deterministic fallback legal-analysis memo quality, following production
feedback after PR #270.

This is **not** an Ollama task. It does not enable Ollama, change the OpenRouter
model policy, or change law-API credentials. It does not hide live-law-lookup
failures with UI wording, invent official citations, or claim direct authority
where none exists.

## 1. Observed production issues

Tested questions:

1. `E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?`
2. `H-1 외국인등록은 언제 해야 하나요?`
3. `G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?`

Shared source-panel / developer diagnostic:

```
실시간 법령 조회 응답을 파싱하지 못했습니다.
직접 법령 인용은 제한됩니다.
--- raw developer codes ---
SOURCE_UNAVAILABLE
LAW_API_BAD_RESPONSE
```

Answer-quality issues:

- E-7 → F-2-99 answer lacked official evidence and ended with a "not grounded
  in the official manual" note.
- H-1 foreigner-registration answer was too vague/source-limited for a
  registration/reporting question.
- G-1-5 deterministic fallback exposed internal field names
  (`current_status/sub_status`, `previous_status/approval_conditions`,
  `target_status/route`, `paid_or_credit_bearing`, `duration/employer_or_school`).
- G-1-5 fallback mixed English official-confirmation questions into a Korean
  answer, included unrelated deadline/address-change questions, and collapsed
  G-1-5 into generic G-1.

## 2. LAW_API_BAD_RESPONSE diagnosis plan

The production single-call path (`build_law_grounding_context` →
`search_laws(target=law)`) classifies any non-OK outcome and adds
`SOURCE_UNAVAILABLE` + the typed error code to `law_grounding_warnings`. When the
live API returned a non-JSON/non-XML body (an HTML service/login page, or a
gateway text), the tool layer correctly classified it as `LAW_API_BAD_RESPONSE`,
but the **diagnostics** then treated that single code as the dominant, whole-of-
lookup verdict and the UI always said "could not be parsed".

Because live Open Law API access is not available in CI / this environment, we
do **not** claim a live success. Instead we:

- harden the parser with safe shape assumptions and a precise status taxonomy;
- distinguish per-family statuses so a single `bad_response` no longer dominates;
- provide an operator capture command (Section 8) to record the *real* shape
  metadata (never raw bodies, never secrets) when run with a configured OC.

Operator capture commands (sanitized metadata only):

```
python3 scripts/capture_law_api_shape.py --family statute --query "출입국관리법 외국인등록"
python3 scripts/capture_law_api_shape.py --family enforcement_decree --query "출입국관리법 시행령 외국인등록 체류자격"
python3 scripts/capture_law_api_shape.py --family enforcement_rule --query "출입국관리법 시행규칙 외국인등록"
python3 scripts/capture_law_api_shape.py --family administrative_rule --query "E-7 근무처 변경 추가 신고"
python3 scripts/capture_law_api_shape.py --family legal_term --query "체류자격외활동"
python3 scripts/capture_law_api_shape.py --family statute --query "F-2-99 거주 취업활동"
python3 scripts/capture_law_api_shape.py --family statute --query "G-1 체류자격 활동범위"
```

## 3. Parser / status taxonomy corrections

`backend/services/law_tools.py`:

- `_official_error_info` no longer flags a **success** `errorCode` (`0` / `00` /
  `OK`) as an official error. Previously any non-empty `error`/`errorCode` value
  — including `0` — was treated as an error, which could push a good response
  toward `official_error` → effective `bad_response`.
- Confirmed status mapping (one outcome → one status, never collapsed):
  - empty body → `LAW_API_NO_RESULTS` (`response_shape_hint=empty`)
  - parseable JSON/XML with zero candidates → `LAW_API_NO_RESULTS`
  - official API error payload (JSON or XML) → `LAW_API_OFFICIAL_ERROR`
    (`parser_status=official_error`)
  - HTML service/login page → `LAW_API_BAD_RESPONSE`
    (`response_shape_hint=html`, no body leak)
  - plain text → `LAW_API_BAD_RESPONSE` (`response_shape_hint=text`)
  - unsupported source family → `unsupported` (not `bad_response`)
  - missing credentials → `not_configured` (not `bad_response`)
  - timeout → `timeout`; HTTP 4xx/5xx → `http_error`
- The reused single-call path now derives a **granular statute-family status**
  (`statute: no_results / official_error / bad_response / ...`) from the live
  result, so the source panel shows real per-family statuses instead of a single
  dominant code.

Shape hints surfaced for capture/debug: `json_object`, `json_list`, `xml`,
`html`, `text`, `empty`, plus `unknown` (capture tooling) and the
`official_error` parser status.

## 4. H-1 foreigner-registration behavior

`H-1 외국인등록은 언제 해야 하나요?`

- Classified as registration/reporting, never school enrollment:
  `proposed_activity_type` includes `registration_or_reporting` (not
  `formal_enrollment`); `legal_issue_types` includes `reporting_duty` and
  `registration_or_residence_report` (not `formal_enrollment`,
  `study_on_non_study_status`); `activity_facts.formal_enrollment == "false"`.
- Source planning now leads with **manual**, then **statute**,
  **enforcement_decree**, **enforcement_rule**, **administrative_rule**,
  legal_interpretation (Enforcement Decree was previously missing for this
  issue family).
- Fallback memo gives a practical registration/reporting framing and asks the
  decisive facts: entry date, granted period of stay, registration deadline,
  and filing channel (HiKorea / competent immigration office). It never
  mentions university, course, credit, or D-2/D-4.

## 5. G-1-5 fallback memo cleanup

`backend/paradiso_backend.py` deterministic fallback (`build_legal_analysis_fallback_answer`):

- The user-facing memo no longer renders the internal `decisive_facts` list
  (snake_case) or the English-canonical `official_confirmation_questions`.
- Natural-language, issue-aware fact bullets are produced via
  `_fallback_fact_lines_localized`.
- Localized, issue-scoped confirmation questions are produced via
  `_fallback_confirmation_questions_localized`. For a G-1-5 study/audit question
  they are exactly:
  - 현재 G-1-5 부여 사유가 무엇인지
  - 등록/청강/계절학기 중 어떤 활동인지
  - 학점 인정 또는 학위 과정 관련성이 있는지
  - 수업 기간과 주당 시간이 얼마인지
  - 학교가 D-2/D-4 등 유학 체류자격을 요구하는지
  - 출입국이 이를 G-1-5 체류 목적과 양립 가능한 활동으로 보는지
  - 자격외활동허가 또는 체류자격 변경이 필요한지
- Unrelated deadline/address-change questions are only emitted for genuine
  registration/reporting issues — never for a study/audit question.
- G-1-5 is preserved as the current status (not collapsed to generic G-1).

## 6. Localized confirmation questions

- `lang=ko` → Korean confirmation questions and fact bullets only.
- `lang=en` → English confirmation questions and fact bullets.
- Other languages reuse the existing localized/canonical sets safely.
- Internal snake_case field names are never exposed to the user in any language.

## 7. E-7 → F-2-99 confidence-gated behavior

For the side-job-after-status-change question:

- No over-confident "더 이상 적용되지 않습니다" unless direct authority supports it
  (existing confidence gate retained and exercised by tests).
- When direct sources are unavailable, the memo states that F-2-99 is the
  primary basis, prior E-7 is related/comparative, and the decisive facts are
  the F-2-99 approval conditions plus the side-activity form / employer /
  industry / hours / compensation.
- Confirmation questions: current ARC = F-2-99?, F-2-99 approval conditions,
  side-job form (employment/freelance/business/incidental), additional
  employer or business registration, industry/hours/compensation/contract, and
  whether immigration treats it as a workplace addition / reportable change /
  activities outside status / a separate restriction.

## 8. Source diagnostics behavior

`ai.html` / `index.html` developer diagnostics (`renderGroundingSourcePanel`):

- Default source panel never shows raw codes; the developer `<details>` block is
  optional and `Copy answer` (`copy_safe_answer`) never includes raw codes.
- Diagnostics now render **per-family statuses** (e.g. `statute: no_results`,
  `enforcement_rule: official_error`, `administrative_rule: unsupported`).
- "실시간 법령 조회 응답을 파싱하지 못했습니다." is shown **only** when a
  parser status is actually `parse_error` / `bad_response` (or
  `law_lookup_error_type` is `LAW_API_PARSE_ERROR` / `LAW_API_BAD_RESPONSE`).
- When all family statuses are `no_results` / `unsupported`, a neutral line is
  shown instead ("직접 인용 가능한 결과를 찾지 못했습니다(파서 오류 아님)").
- Raw developer codes remain only at the bottom of the diagnostics block.

## 9. Tests added

- `backend/tests/test_law_tools.py`: `LawParserTaxonomyTests` (XML official
  error, XML success errorCode=0, nested empty → no_results, list under
  body/result, shape-hint coverage) and `OfficialSourceFamilyAdapterTests`
  (unsupported, unknown, not_configured, no_results, official_error, timeout,
  html, results_found).
- `backend/tests/test_law_api_shape_fixtures.py` + synthetic fixtures under
  `backend/tests/fixtures/law_api_shapes/`.
- `backend/tests/test_generalized_legal_issue_source_planning.py`: H-1
  registration classification + source-plan priority (manual first,
  enforcement_decree present).
- `backend/tests/test_legal_analysis_deterministic_fallback.py`: G-1-5 Korean
  fallback has no internal field names, no English official questions, no
  unrelated deadline/address questions, includes G-1-5-specific questions; H-1
  registration fallback asks registration facts and has no study terms; English
  fallback stays English.
- `backend/tests/test_ai_shell_source_semantics.py`: developer diagnostics use
  per-family statuses and only label parser failure when the parser truly
  failed.
- `scripts/smoke_ai_live_quality.py`: WARN-only checks for snake_case labels in
  Korean fallback, English questions in Korean fallback, study terms in
  registration answers, all-family-collapse-to-bad_response, no_results
  misclassified as bad_response, and parser-failure mislabeling.

## 10. Known limitations

- The live Open Law API may still return **no direct authority** for some
  immigration questions; the fallback is a structured preparation note, not a
  citation.
- Some official source families (legal_interpretation, precedent,
  administrative_appeal, constitutional_decision, intelligent_search) remain
  **unsupported / planned-not-wired** and are reported as `unsupported`, not as
  parser failures.
- The deterministic fallback memo is rule-based, not a full LLM memo.

## 11. Safety note

No OC / API-key values are logged, returned, or committed. Source URLs are
sanitized at the tool boundary. The parser never echoes raw response bodies.
The fallback memo and confidence gate avoid inventing citations, documents,
deadlines, penalties, or final eligibility/approval/denial outcomes, and always
route the user to 1345 / HiKorea / the competent immigration office for
confirmation.
