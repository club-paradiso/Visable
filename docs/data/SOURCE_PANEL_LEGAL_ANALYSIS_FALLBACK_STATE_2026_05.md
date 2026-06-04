# Source panel legal-analysis fallback state (2026-05)

## 1. Problem

After the legal-analysis fallback answer body was repaired, the answer for the E-7 → F-2-99 side-job scenario no longer leaked the older H-1 summer-course fallback. The visible source/verification panel, however, could still lead with raw lookup-failure language such as `SOURCE_UNAVAILABLE` and `LAW_API_BAD_RESPONSE` or the Korean equivalent of “law source unavailable.”

That made a structured legal-analysis answer look like a total product failure even when Paradiso had extracted immigration facts, activity types, legal issue types, and a preparation-note analysis.

## 2. Product principle

Paradiso should distinguish source failure from structured legal-analysis availability.

A live law/manual lookup failure remains important operator metadata, but it must not become the dominant user-facing source-panel message when the answer is actually based on structured `legal_analysis`, `immigration_facts`, `legal_issue_types`, and activity classification.

## 3. Source panel state taxonomy

The normalized `source_panel_state` values are:

- `direct_source_verified` — direct manual/law evidence or verified citation exists.
- `manual_grounding_available` — official manual grounding is available.
- `law_grounding_available` — law grounding is available.
- `related_legal_context_available` — related/contextual legal analysis exists, but not direct authority.
- `structured_legal_analysis_available` — structured legal analysis exists and can support the panel message.
- `structured_fallback_available` — deterministic fallback answer used structured legal analysis.
- `no_direct_authority_found` — no direct authority for the scenario was found, but this is not pure system failure.
- `live_law_lookup_technical_issue` — live law lookup hit a technical issue without structured analysis taking precedence.
- `source_unavailable` — no source and no structured legal analysis are available.

## 4. UI copy changes

For deterministic fallback with legal analysis:

- Korean label: “구조화된 법률 분석 메모”
- English label: “Structured legal analysis note”

For legal analysis with a bad live law API response:

- Korean label: “구조화된 법률 분석 사용”
- English label: “Structured legal analysis used”

For related/contextual legal analysis:

- Korean label: “관련 법적 맥락 분석”
- English label: “Related legal context analysis”

Simplified/traditional Chinese labels are also present so required source-panel keys do not break those locales.

## 5. Technical details behavior

Raw internal diagnostics such as `SOURCE_UNAVAILABLE`, `LAW_API_BAD_RESPONSE`, and `CITATION_VERIFICATION_NOT_WIRED` may remain visible only in collapsed developer diagnostics.

The default source-panel summary must not show these codes as the primary label, and copy-answer behavior must copy only the answer text, not developer diagnostics.

## 6. Tests added

The regression coverage checks:

- deterministic fallback plus `legal_analysis` maps to `structured_fallback_available`;
- legal analysis plus law lookup failure maps to structured-analysis copy instead of source-unavailable copy;
- pure no-source/no-legal-analysis maps to `source_unavailable`;
- technical codes remain in collapsed diagnostics, not default labels;
- E-7 → F-2-99 fallback does not leak H-1 study template wording;
- copy-safe answers do not include raw diagnostics;
- Korean, English, simplified Chinese, and traditional Chinese required source-panel keys exist.

## 7. Known limitations

- The live law API can still fail or return unusable data.
- Structured legal analysis is not direct citation and does not pretend to be official law/manual authority.
- The final agency determination remains with 1345, HiKorea, the competent immigration office, or other qualified official/professional channels.

## 8. Safety note

This change improves source-panel transparency without hiding technical failures. It separates user-facing trust language from developer diagnostics and preserves the caution that structured legal analysis is preparatory reference information, not an official decision or invented authority.
