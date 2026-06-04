# Official Law Source Retrieval Adapters (2026-05)

## Problem

Recent source-panel and deterministic fallback work improved how Paradiso presents legal-analysis availability when live law lookup fails. That was not enough: the underlying official-source retrieval layer could still collapse empty official results, official API errors, unsupported source families, and parser failures into generic `LAW_API_BAD_RESPONSE`-style diagnostics. This PR hardens the retrieval adapters so Paradiso can attempt real official evidence retrieval while keeping failures typed, safe, and non-dominant in user-facing source states.

## Official source family model

Paradiso now treats official evidence as source families rather than a single generic law search. Wired families are:

- `statute`
- `enforcement_decree`
- `enforcement_rule`
- `administrative_rule`
- `legal_term`

Planned but not fully endpoint-mapped families are explicitly marked unsupported instead of bad-response:

- `legal_interpretation`
- `precedent`
- `administrative_appeal`
- `constitutional_decision`
- `intelligent_search`

Manual evidence remains a separate family because manual retrieval is not an Open Law API call.

## Safe response-shape capture helper

`scripts/capture_law_api_shape.py` samples Open Law API response shapes without printing or storing `LAW_API_OC`, `LAW_API_KEY`, or credential-like query parameters. It follows backend credential precedence (`LAW_API_OC` first, `LAW_API_KEY` fallback), supports per-family sample queries, emits metadata only by default, and can optionally write sanitized metadata fixtures to `backend/tests/fixtures/law_api_shapes/`.

Captured metadata includes HTTP status, content type, encoding, sanitized URL, response-shape hint, parser status, JSON root keys or XML root tag where safe, list counts where safe, and official error code/message if detected.

## Parser statuses and response shape hints

Response-shape hints are intentionally coarse and safe:

- `json_object`
- `json_list`
- `xml`
- `html`
- `text`
- `empty`
- `unknown`

Parser statuses distinguish successful parsing from empty payloads, unsupported HTML/text, malformed JSON/XML, and official error payloads. Raw response bodies are not returned to callers or LLM metadata.

## Source-family status taxonomy

Adapter results use explicit source-family statuses:

- `results_found`
- `no_results`
- `official_error`
- `http_error`
- `timeout`
- `bad_response`
- `parse_error`
- `unsupported`
- `not_configured`

Unsupported or planned-but-not-wired families do not become `LAW_API_BAD_RESPONSE`.

## Normalized evidence schema

Official-source items are normalized to a secret-free schema:

```json
{
  "source_type": "statute|enforcement_decree|enforcement_rule|administrative_rule|legal_interpretation|precedent|administrative_appeal|constitutional_decision|legal_term|manual",
  "title": "...",
  "law_name": "...",
  "article": "...",
  "case_name": "...",
  "case_number": "...",
  "decision_date": "...",
  "summary": "...",
  "query": "...",
  "source_url": "sanitized",
  "retrieval_status": "...",
  "relevance": "direct|related|analogical|background|not_relevant"
}
```

## Relevance scoring rules

Normalized source-family evidence is scored consistently:

1. Current status plus matching legal issue concept can become direct or related depending specificity.
2. Previous-status-only evidence is related/comparative, not direct, when a current status exists.
3. Target-status evidence in status-change questions is route-related or direct only when the source family and issue match.
4. General statute concepts without a status match remain background.
5. Legal terms remain background unless tied to the exact issue.
6. Administrative appeal and precedent evidence is direct only for the same status and issue; otherwise it is related or analogical.
7. Related or analogical evidence is not promoted to direct authority.

## Debug and smoke fields

Debug/smoke metadata now includes:

- `source_families_planned`
- `source_families_attempted`
- `source_family_statuses`
- `source_family_result_counts`
- `response_shape_hint_by_family`
- `parser_status_by_family`
- `law_error_type_by_family`
- `normalized_evidence_count`
- direct/related/analogical/background evidence counts
- `sanitized_source_urls`
- legal-analysis confidence
- source-panel state

## Tests added

Tests cover parser hardening, JSON/XML shape handling, official error classification, empty/no-result classification, HTML/text fallback behavior, malformed payloads, URL sanitization, source-family statuses, no raw response-body propagation, source planning for representative visa scenarios, and source-panel fallback semantics.

## Known limitations

- The live Open Law API may still return no direct scenario-specific source for a user’s exact facts.
- Some source families remain unsupported until endpoint-specific adapters are fully mapped and verified.
- Legal analysis is not a final agency determination.

## Safety note

Paradiso provides source-grounded legal and immigration guidance for preparation. It does not determine final eligibility, permission, approval, denial, or required documents.
