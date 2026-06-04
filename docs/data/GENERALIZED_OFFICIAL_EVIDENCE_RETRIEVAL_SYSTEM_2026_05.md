# Generalized Official-Evidence Retrieval System (2026-05)

This note documents the generalized official-evidence retrieval system: a
reusable ontology + query-planning + routing + relevance layer that handles
arbitrary Korean visa/residence questions by reasoning over structured *issue
dimensions* rather than memorizing individual scenarios.

Companion docs:

- `docs/data/AI_ANSWER_PIPELINE_CONTRACT_AND_RENDERING_2026_05.md` (frontend/backend contract)
- `docs/data/AI_ANSWER_SHELL_SOURCE_SEMANTICS_2026_05.md` (source-panel semantics)
- `docs/data/LIVE_LAW_PARSING_AND_FALLBACK_MEMO_QUALITY_2026_05.md` (law parsing + fallback)
- `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md` (disclosure state classes)

Core module: `backend/services/evidence_ontology.py`.

## 1. Why this is not a case-by-case patch

H-1, G-1-5, E-7, F-2-99, C-3 and D-2 are **regression and evaluation cases
only** — they do not appear as branch conditions in production logic. The system
decomposes any question into structured dimensions and applies one general
pipeline:

```
question
  → immigration fact extraction         (legal_analysis.extract_immigration_facts)
  → activity / procedure classification (legal_analysis.classify_activity_types)
  → legal issue classification          (legal_analysis.classify_legal_issue_types)
  → source family routing               (evidence_ontology.route_source_families)
  → query generation                    (evidence_ontology.plan_evidence_queries)
  → official source retrieval           (law_tools.retrieve_planned_official_sources)
  → evidence normalization              (law_tools._normalize_candidate)
  → relevance scoring                   (legal_analysis.score_evidence_relevance)
  → answer confidence level             (answer_quality / legal_analysis)
  → source panel state                  (paradiso_backend._derive_source_panel_metadata)
```

Visa codes enter only as *values* of status-role dimensions (current /
previous / target), never as `if visa == "H-1"` branches. The routing table and
query planner are keyed by legal-issue and procedure dimensions, so a new visa
code or scenario is handled by the same general rules.

## 2. Ontology dimensions

Defined once in `evidence_ontology.py`:

- **Status roles** — `current_status`, `current_parent_status`,
  `current_sub_status`, `previous_status`, `previous_parent_status`,
  `previous_sub_status`, `target_status`, `target_parent_status`,
  `target_sub_status`, `status_transition_detected`.
- **Status families** (generalized groupings for query expansion) — `study`,
  `work`, `residence`, `short_term`, `humanitarian`, `jobseeking`,
  `diplomatic_official`, `other`. Membership is by parent code only.
- **Activity dimensions** — credit-bearing study, formal enrollment,
  audit/non-credit, language training, paid work, unpaid/paid internship,
  freelance, side job, additional employment, business activity, volunteer,
  workplace change/addition, medical, litigation, family/marriage, refugee/
  humanitarian, registration/reporting, re-entry/departure, document
  preparation, status extension, status-change route.
- **Procedure dimensions** — extension, status change, activities outside
  status, workplace change/addition, foreigner registration, address/residence
  report, re-entry permit, status grant, document checklist,
  deadline/reporting duty, overstay/risk.
- **Legal issue dimensions** — activity_scope, outside_status_activity,
  status_purpose_alignment, reporting_duty, registration_or_residence_report,
  workplace_change_addition, status_change, documents_needed,
  employment_restriction, study_on_non_study_status, work_on_non_work_status,
  post_status_change_residual_duty, approval_condition, deadline_trigger,
  overstay_or_risk, nationality_or_refugee_context, extension, reentry,
  legal_general, non_immigration_adjacent_issue.
- **Source families** — manual, statute, enforcement_decree, enforcement_rule,
  administrative_rule, legal_term (all *wired*); legal_interpretation,
  administrative_appeal, precedent, constitutional_decision, intelligent_search
  (*planned-not-wired* until an adapter exists).
- **Evidence goals** — direct, contextual, analogical, background, not_relevant.

## 3. Query planner design

`plan_evidence_queries(immigration_facts, legal_issue_types, ...)` deterministically
maps ontology dimensions to structured query objects:

```json
{
  "source_family": "statute",
  "priority": 2,
  "query_ko": "출입국관리법 H-1 체류자격 활동범위",
  "query_en": "Immigration Control Act H-1 activity scope of status",
  "status_role": "current_status",
  "expected_status_codes": ["H-1"],
  "expected_concepts": ["체류자격 활동범위", "activity_scope"],
  "evidence_goal": "direct",
  "reason": "Issue 'activity_scope' routes to 'statute' (wired); anchored on current_status=H-1; goal=direct."
}
```

Properties:

- **Composable templates** — source-family term + status anchor (code or status
  family name) + issue concept + procedure term. Korean official terms lead for
  Korean-source retrieval; an English mirror is included.
- **Status roles preserved** — current is anchored first (controlling status),
  then target (route) and previous (comparative).
- **Deterministic cap + dedup** — capped (`max_queries`, hard cap 12), deduped by
  `(family, role, code, issue)` and by Korean query text.

## 4. Source-family routing

`SOURCE_FAMILY_ROUTING` in `evidence_ontology.py` is the **single source of
truth** for issue → ordered source-family priority. `route_source_families()`
expands a set of issues in order, first occurrence wins.
`legal_analysis.build_generalized_source_plan()` now consumes this table (the
former inline if/elif ladder was removed) so routing lives in one place.

Representative rules (manual leads for procedure/document/registration; statute
family leads for activity-scope/authority):

| Issue | Routed source families (priority order) |
|---|---|
| registration_or_residence_report / reporting_duty / workplace_change_addition | manual → statute → enforcement_decree → enforcement_rule → administrative_rule → legal_interpretation |
| activity_scope / outside_status_activity / study_on_non_study_status / work_on_non_work_status | statute → enforcement_decree → enforcement_rule → administrative_rule → legal_interpretation → administrative_appeal → manual |
| status_change | manual → statute → enforcement_decree → legal_interpretation → administrative_appeal |
| documents_needed | manual → statute → enforcement_rule (manual is the checklist authority) |
| overstay_or_risk | statute → enforcement_decree → enforcement_rule → administrative_appeal |

Unsupported families are reported as `unsupported` / `planned_not_wired`, never
as a parser `bad_response`.

## 5. Evidence relevance rules

`score_evidence_relevance()` respects status role and legal issue:

1. Evidence matching the current status + the legal-issue concept → **direct**.
2. Evidence matching only the current *parent* status → **contextual** (related),
   unless an exact sub-status is required.
3. Evidence matching only the *previous* status (after a transition) →
   **related/analogical** (comparative), never direct.
4. Evidence matching the *target* status in a status-change question →
   target-route evidence (direct for primary authority families).
5. General legal terms are **background** unless paired with the exact issue +
   status; they never become direct authority.
6. Manual evidence can be direct for procedures/documents/reporting.
7. Law evidence can be direct for legal authority/activity scope, but **law-only
   evidence never creates a required-document checklist** — `documents_needed`
   routes the manual first.
8. Related/analogical evidence is never promoted to direct.
9. If no direct evidence exists, `answer_certainty_level` stays contextual /
   limited / unavailable.

## 6. Evidence confidence levels

`answer_certainty_level` ∈ {`direct`, `contextual`, `analogical`, `limited`,
`unavailable`} is derived from the deterministic relevance buckets
(`direct_evidence_count`, `related_evidence_count`, `analogical_evidence_count`,
`background_evidence_count`). Counts are deterministic for a given question, so
two identical questions yield identical confidence and source-panel state.

## 7. Regression test examples (generalized assertions only)

`backend/tests/test_generalized_evidence_ontology.py` asserts generalized
outputs (dimensions, routing, goals, counts) — never hardcoded answer strings:

1. `H-1 외국인등록은 언제 해야 하나요?` → registration/reporting; not
   study/enrollment; manual in plan; no D-2/D-4 in planned status codes.
2. `E-7에서 F-2-99로 변경 후 부업…` → previous=E-7, current/target=F-2-99;
   previous-status queries are comparative, not direct.
3. `G-1-5로 체류 중…대학교 등록/청강/계절학기` → G-1-5 preserved;
   study_on_non_study_status; D-2/D-4 never the queried status.
4. `Can I change status to F-2-99?` (+ H-1 separately) → current=H-1,
   target=F-2-99; target-route query present; H-1 preserved.
5. `C-3 단기방문으로 paid work…` → paid work on short-term status; no invented
   penalties.

The 10 ontology/planner unit-test requirements (one query per issue, registration
≠ enrollment, role preservation, unsupported ≠ bad_response, empty → no_results,
legal-term → background, law-only ≠ checklist, previous-status comparative,
target-status route, deterministic counts) all pass.

## 8. Live capture batch

`scripts/capture_law_api_shape.py --batch immigration-core` runs an
ontology-generated batch (from `evidence_ontology.build_immigration_core_batch`,
not a disconnected list) across representative families and issue types:
registration/reporting, activity outside status, workplace change/addition,
status change, study on non-study status, paid work on short-term status,
document checklist, legal-term lookup.

Output is fully sanitized — no OC/API-key leakage, no raw response bodies — and
reports per record: `source_family`, `query`, `response_shape_hint`,
`parser_status`, `source_family_status`, `normalized_count`, `safe_error_type`.
Unwired families report `planned_not_wired`/`unsupported`; the manual reports
`not_api_retrievable` (it is grounded locally, not via the Open Law API). With
no credentials the batch records `not_configured` and makes **no** network call,
so it is safe in CI.

## 9. Known limitations

- Official sources may not contain a direct answer for every scenario; the
  system then honestly reports contextual / limited / unavailable rather than
  inventing direct authority or citations.
- Unsupported source families (legal_interpretation, administrative_appeal,
  precedent, constitutional_decision, intelligent_search) remain incremental —
  they are planned and labeled `planned_not_wired` until adapters are wired.
- The deterministic layer prepares evidence and confidence; the final agency
  determination (1345 / HiKorea / the competent immigration office) is always
  still required.

## 10. Safety note

This work does not invent citations, does not pretend direct authority exists
when only contextual/analogical authority does, does not weaken source-confidence
rules, and does not change OpenRouter/Ollama/provider policy or credentials. It
generalizes how official evidence is planned, routed, retrieved, and scored —
honestly surfacing source limitations rather than hiding them.
