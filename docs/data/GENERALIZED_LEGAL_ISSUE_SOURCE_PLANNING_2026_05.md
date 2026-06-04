# Generalized Legal Issue Source Planning (2026-05)

## 1. Why case-by-case prompts are not sustainable

Prior improvements covered important scenarios (for example H-1 summer study, G-1-5 university activity, and E-7 to F-2-99 side work), but a legal guidance engine cannot depend on adding a bespoke prompt or branch for every visa/activity combination. Korean residence questions combine status, sub-status, activity, timing, compensation, reporting duties, and approval conditions in many permutations. Paradiso now treats those examples as regression cases for a generalized deterministic pipeline.

## 2. Immigration fact extraction schema

The backend prepares an `immigration_facts` object before generation:

```json
{
  "current_status": null,
  "current_parent_status": null,
  "current_sub_status": null,
  "previous_status": null,
  "previous_parent_status": null,
  "previous_sub_status": null,
  "target_status": null,
  "target_parent_status": null,
  "target_sub_status": null,
  "status_transition_detected": false,
  "proposed_activities": [],
  "activity_facts": {
    "credit_bearing": "unknown",
    "degree_related": "unknown",
    "paid": "unknown",
    "formal_enrollment": "unknown",
    "institution_registered": "unknown",
    "duration_known": "false",
    "employer_or_client_known": "false",
    "business_registration_issue": "unknown",
    "approval_condition_issue": "unknown"
  },
  "user_question_language": "unknown"
}
```

The extractor preserves sub-statuses such as `G-1-5` and `F-2-99`, detects transitions such as `E-7 -> F-2-99`, keeps current status primary for current activity analysis, and marks unknown facts as `unknown` rather than silently converting them to `false`.

## 3. Legal issue taxonomy

One question may have multiple deterministic issue types:

- `activity_scope`
- `outside_status_activity`
- `status_change`
- `extension`
- `documents_needed`
- `reporting_duty`
- `workplace_change_addition`
- `registration_or_residence_report`
- `reentry`
- `overstay_or_risk`
- `approval_condition`
- `status_purpose_alignment`
- `employment_restriction`
- `study_on_non_study_status`
- `work_on_non_work_status`
- `post_status_change_residual_duty`
- `nationality_or_refugee_context`
- `legal_general`
- `non_immigration_adjacent_issue`

The taxonomy is driven by extracted status/activity facts plus multilingual legal signals, not by a single hard-coded scenario branch.

## 4. Activity classifier

The reusable classifier emits a list of proposed activity categories, including credit-bearing study, formal enrollment, non-credit audit, cultural/hobby study, language training, paid work, paid/unpaid internship, freelance work, side job, additional employment, business activity, workplace change/addition, medical treatment, litigation stay, family/marriage, refugee/humanitarian context, registration/reporting, re-entry/departure, document preparation, extension, and status-change route.

It handles Korean and English keywords deterministically and can return multiple categories for one question.

## 5. Source planning by legal issue type

Source planning is now derived from `legal_issue_types + immigration_facts`:

- `documents_needed`: manual first; law only as authority/background; no law-only checklist.
- `activity_scope` / `outside_status_activity`: statute, enforcement decree/rule, administrative rules, interpretations, administrative appeals, and manual where status-specific guidance exists.
- `status_change`: manual, statute/enforcement decree, interpretations, and administrative appeal context where supported.
- `reporting_duty` / `workplace_change_addition`: manual, statute, enforcement rule, administrative rule, interpretation.
- `overstay_or_risk`: statute, enforcement decree/rule, administrative appeal; no invented penalty amount.
- `nationality_or_refugee_context`: relevant law family such as nationality/refugee law while clarifying Paradiso's visa/residence focus.
- `post_status_change_residual_duty`: current status authority first, previous status as related/comparative, approval conditions as decisive facts, and reporting/workplace rules as issue-specific sources.

Query count remains capped, and unsupported families are represented in debug metadata without forcing live calls in CI.

## 6. Legal analysis object construction

The backend constructs `legal_analysis` before the LLM runs. Required fields include:

- `analysis_mode`
- `main_issue`
- `sub_issues`
- `legal_issue_types`
- `immigration_facts`
- `relevant_legal_concepts`
- `source_types_attempted`
- `direct_authority`
- `related_authority`
- `analogical_authority`
- `background_authority`
- `missing_direct_authority`
- `risk_posture`
- `confidence`
- `practical_posture`
- `decisive_facts`
- `official_confirmation_questions`
- `authority_summary`

The LLM may explain this object but must not invent it.

## 7. Evidence relevance scoring

Evidence is scored as direct, related, analogical, background, or not relevant. Direct authority must match the current status (and retained sub-status where applicable) plus the legal/activity concept. Previous-status evidence remains related or analogical unless the issue is residual duty, approval condition, or reporting tied to that prior status.

## 8. Issue-based answer templates

Templates are selected by issue type, not individual visa examples:

1. Study/activity on non-study status
2. Work/activity on non-work or restricted status
3. Post-status-change residual duty
4. Workplace change/addition/reporting duty
5. Status change route
6. Document checklist
7. Extension/high-risk exception
8. Overstay/risk
9. Registration/reporting
10. Nationality/refugee context
11. Non-immigration adjacent issue

Each template starts with practical legal posture, identifies current status/activity/issue, explains source-grounded legal analysis, states source basis later, asks decisive facts, and avoids final administrative determination.

## 9. Regression examples, not product logic

H-1, G-1-5, and E-7 -> F-2-99 are now regression examples that verify the generalized pipeline. They should not become primary logic branches, and future visa/activity combinations should be covered by the same fact extraction, taxonomy, activity classifier, source plan, evidence scoring, and template selection.

## 10. Matrix/property-style tests

Matrix tests cover status families, activity categories, issue types, previous/current status transitions, workplace additions, and approval-condition signals. These reduce the need to manually add every future scenario snapshot.

## 11. Smoke/debug fields

Smoke/debug metadata includes:

- `immigration_facts`
- `legal_issue_types`
- `proposed_activity_type`
- `source_plan`
- `legal_analysis.analysis_mode`
- `risk_posture`
- `confidence`
- `decisive_facts`
- `official_confirmation_questions`
- `first_sentence_quality_warning`
- `raw_code_default_ui_leak`

## 12. Known limitations

- The deterministic classifier is intentionally conservative and may mark facts `unknown` when a user omits details.
- Some source families are planned but not yet fully retrievable by the current Open Law API adapter.
- Legal interpretations, precedents, and administrative appeals require careful normalization before they can be treated as strong evidence.
- The system does not infer document lists from law-only sources.

## 13. Safety note

Paradiso provides source-grounded legal and immigration guidance for preparation. It does not determine final eligibility, permission, approval, denial, or required documents. Users must confirm case-specific outcomes with 1345, HiKorea, or the competent immigration office.
