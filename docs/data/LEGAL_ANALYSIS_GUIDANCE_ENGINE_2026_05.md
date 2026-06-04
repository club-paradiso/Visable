# Legal Analysis Guidance Engine (2026-05)

## Product purpose

Paradiso is a source-grounded Korean visa and residence legal-guidance chatbot. Its value is not generic caution; it should analyze official manuals, statutes, enforcement decrees/rules, administrative rules, legal interpretations, precedents, administrative appeal decisions, and adjacent official sources to give legally useful, issue-based preparation guidance.

## Boundary

Paradiso provides legal analysis and practical guidance for preparation. It does **not** make the final administrative decision, guarantee eligibility, approval, denial, permission, or document completeness, or replace 1345, HiKorea, or the competent immigration office.

## Why failure-first framing harms trust

Starting ordinary answers with “Paradiso cannot verify …” makes the product look like a source-audit bot even when related official legal concepts can support useful analysis. The legal-analysis engine therefore leads with the strongest supportable practical posture, then states the source limitation, then explains the legal issue and concrete confirmation questions.

## Legal analysis object schema

The backend deterministically prepares a `legal_analysis` object before LLM generation. The LLM may explain this object but must not invent it from scratch.

```json
{
  "analysis_mode": "direct_authority|contextual_authority|analogical_analysis|limited_authority|source_unavailable|not_applicable",
  "main_issue": "...",
  "sub_issues": ["..."],
  "relevant_legal_concepts": ["..."],
  "source_types_attempted": ["statute", "enforcement_decree"],
  "source_types_returned": ["statute"],
  "source_type_statuses": {"statute": "results_found"},
  "direct_authority": [],
  "related_authority": [],
  "analogical_authority": [],
  "background_authority": [],
  "missing_direct_authority": true,
  "risk_posture": "low|medium|high",
  "confidence": "direct|contextual|analogical|limited|unavailable",
  "practical_posture": "...",
  "official_confirmation_questions": ["..."],
  "direct_evidence_count": 0,
  "related_evidence_count": 0,
  "analogical_evidence_count": 0,
  "background_evidence_count": 0,
  "authority_summary": "..."
}
```

## Source types and source planning

The source planner considers these families:

1. manual
2. statute / 법령
3. enforcement decree / 시행령
4. enforcement rule / 시행규칙
5. administrative rule / 행정규칙
6. legal interpretation / 법령해석례
7. precedent / 판례
8. administrative appeal / 행정심판례
9. constitutional decision / 헌재결정례
10. legal term / 법령용어
11. intelligent search / 지능형 법령검색

Each family is marked as `attempted`, `not_attempted`, `unsupported`, `unavailable`, `no_results`, `results_found`, or `parse_error`. The current Open Law API layer safely supports statute-family law search, administrative rules, and legal terms; other families are scaffolded and marked unsupported until wired.

Planning priorities include:

- `activity_on_status`: statute family, legal interpretations, administrative appeals.
- `status_change`: manual, statute family, legal interpretations, administrative appeals.
- `documents_needed`: manual first; law only as background, never as a law-only checklist.
- `deadline_or_report`: statute/decree/rule, manual, administrative rules.
- `high_risk_exception`: statute family, legal interpretations, administrative appeals, and precedents when high-signal.
- `overstay_or_risk`: statute family and administrative appeals; no invented penalties.
- `nationality_or_refugee_context`: relevant statute family while clarifying Paradiso’s visa/residence focus.

## Evidence relevance scoring

Each evidence item is scored deterministically:

- `direct`: exact status + exact procedure/activity scenario.
- `related`: same legal concept or adjacent status, but not exact scenario.
- `analogical`: useful comparison but not controlling.
- `background`: general legal context or terminology.
- `not_relevant`: unrelated.

Related or analogical evidence is never displayed as direct authority. For example, D-2/D-4 study materials in an H-1 study question are related/analogical comparison context, not direct H-1 authority.

## H-1 summer-course example

**Before:**

> Paradiso cannot verify that an H-1 holder may take a credit-bearing or degree-related university summer course in Korea …

**After:**

> Treat a credit-bearing or degree-related university summer course as a high-risk activity under H-1 until immigration confirms otherwise. The central legal issue is whether immigration treats the course as within H-1’s permitted activity scope or as activities outside the scope of status requiring separate permission or a change of sojourn status.

Then Paradiso states that direct scenario-specific authority was not found, distinguishes related D-2/D-4 study context from direct H-1 authority, and asks concrete confirmation questions about credits, degree relationship, hours, enrollment period, whether study becomes the main stay purpose, H-1 work continuation, and whether the university requires D-2/D-4.

## Official confirmation as analysis support

“Confirm with 1345/HiKorea/the competent office” is not a substitute for analysis. Paradiso should tell the user:

- the legal issue to ask about;
- the facts to prepare;
- likely decision variables;
- safely framed consequences of acting without confirmation;
- statuses/procedures to mention, such as H-1, D-2/D-4, 체류자격외활동, and 체류자격 변경.

## Source panel semantics

The source panel now communicates legal-analysis value, not only source availability:

- Direct official authority found
- Related legal context checked
- Analogical legal analysis
- No direct scenario-specific authority found
- Official confirmation still required
- Source lookup unavailable
- Source lookup technical issue

Raw codes such as `SOURCE_UNAVAILABLE`, `LAW_API_BAD_RESPONSE`, and `CITATION_VERIFICATION_NOT_WIRED` belong only in collapsed technical details.

## Tests added

Tests cover:

- H-1 legal-analysis object creation;
- main issue and risk/confidence/missing-direct-authority fields;
- concrete official confirmation questions;
- evidence scoring for direct, related, analogical/background, and irrelevant evidence;
- D-2/D-4 not promoted to direct H-1 authority;
- source-family planning by question type;
- answer directive first-line framing;
- source-panel labels and raw-code containment.

## Smoke/debug fields

The API/debug metadata exposes:

- `legal_analysis`
- `analysis_mode`
- `main_issue`
- `risk_posture`
- `confidence`
- `source_types_attempted`
- `source_types_returned`
- `direct_evidence_count`
- `related_evidence_count`
- `analogical_evidence_count`
- `background_evidence_count`
- `missing_direct_authority`
- `source_state`
- `answer_first_sentence`
- `first_sentence_quality_warning`

The smoke script warns on failure-first legal/procedure answers, missing `legal_analysis`, raw source codes in default UI, mislabeled related evidence, and missing concrete official-confirmation questions.

## Known limitations

- Official sources may not contain exact scenario-specific authority.
- Law/precedent evidence may be contextual or analogical rather than directly controlling.
- Final determination remains with the competent authority.
- Live APIs may fail, be disabled, return no results, or return unsupported shapes.

## Safety note

Paradiso provides source-grounded legal and immigration guidance for preparation. It does not determine final eligibility, permission, approval, denial, or required documents. Users must confirm case-specific outcomes with 1345, HiKorea, or the competent immigration office.
