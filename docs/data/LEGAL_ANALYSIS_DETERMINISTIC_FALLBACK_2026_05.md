# Legal-analysis deterministic fallback (2026-05)

## Problem

After PR #266 introduced generalized immigration issue extraction, the LLM-outage deterministic fallback still used an older H-1 summer-semester preparation-note template. When a user asked:

> E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?

Paradiso correctly disclosed temporary AI model unavailability, but then showed H-1 / university summer-semester language about credit-bearing coursework, H-1 activity scope, and D-2/D-4 comparison statuses. That was unrelated to the user's E-7 → F-2-99 side-job/reporting-duty question.

## Root cause

`backend/paradiso_backend.py` built deterministic fallback answers with a localized hardcoded H-1 study template. The fallback path did not consume the generalized `legal_analysis` object added by PR #266, even though the backend had already extracted immigration facts, legal issue types, proposed activity types, source-plan metadata, decisive facts, and official-confirmation questions.

## Fix

Deterministic fallback answers now use the generalized legal-analysis engine and extracted immigration facts. The fallback builder reads:

- `immigration_facts`
- `legal_issue_types`
- `proposed_activity_type`
- `legal_analysis.main_issue`
- `legal_analysis.practical_posture`
- `legal_analysis.sub_issues`
- `legal_analysis.decisive_facts`
- `legal_analysis.official_confirmation_questions`
- `source_plan` / `source_state`

The response metadata marks this mode as `fallback_answer_kind=legal_analysis_preparation_note` and `legal_analysis_exists=true`. When legal analysis exists, the source state is not presented as a pure source-failure outcome solely because the LLM provider is unavailable.

## Examples

### E-7 → F-2-99 side job

For an E-7 → F-2-99 side-job/reporting-duty question, the fallback now frames the issue around the current F-2-99 status, the previous E-7 conditions as comparative facts, side-job activity type, and reporting/workplace-change issues. It must not mention H-1, university summer semester, credit-bearing coursework, D-2/D-4, or enrollment unless the user's facts introduce those concepts.

### H-1 study

For an H-1 credit-bearing summer-course question, the fallback still discusses H-1, study activity, credit-bearing coursework, activity scope, purpose alignment, and official confirmation questions. This now comes through `legal_analysis` classifications such as `study_on_non_study_status` and `credit_bearing_study`, not a hardcoded deterministic fallback template.

### G-1-5 study/audit

For a G-1-5 question about university registration, auditing, or summer courses, the fallback stays G-1-5-specific. It may surface D-2 / D-4 only as study-status comparison questions when the study facts require it, and it must not leak H-1 wording.

### H-1 foreigner registration

For `H-1 외국인등록은 언제 해야 하나요?`, the fallback treats `등록` as alien registration / residence reporting, not school enrollment. It should surface `registration_or_residence_report`, `reporting_duty`, and `registration_or_reporting`, without summer-semester, credit-course, university-course, or D-2/D-4 language.

### H-1 → F-2-99 status change

For `Can I change status to F-2-99?` with selected/current `visa_code=H-1`, the fallback preserves `current_status=H-1`, `target_status=F-2-99`, `status_transition_detected=true`, and planned law queries containing F-2-99. It frames the answer as a target-status route question rather than reducing it to H-1 activity scope.

## Tests added

Regression coverage includes provider-unavailable / all-candidates-failing fallback behavior for:

1. E-7 → F-2-99 side-job fallback with no H-1 study-template leak.
2. H-1 summer-course fallback through legal analysis.
3. G-1-5 study/audit fallback with no H-1 leak.
4. H-1 alien-registration fallback that does not become school enrollment.
5. H-1 → F-2-99 target-route fallback.
6. First-sentence guard for deterministic fallback answers.
7. Source-panel metadata guard against unrelated H-1 / D-2 / D-4 chips in the E-7 → F-2-99 side-job fallback.

The smoke script also reports deterministic fallback kind, legal-analysis existence, immigration facts, legal issue types, proposed activity type, unrelated H-1 study-template detection, and raw-code default UI leak status.

## Remaining limitation

The deterministic fallback is a structured preparation note, not an LLM-generated legal memo. It organizes extracted facts, issue taxonomy, source boundaries, and official-confirmation questions; it does not provide a final administrative determination.

## Safety note

Paradiso provides source-grounded legal and immigration guidance for preparation. It does not determine final eligibility, permission, approval, denial, or required documents. Final case-specific decisions and operational requirements must be confirmed with 1345, HiKorea, or the competent immigration office.
