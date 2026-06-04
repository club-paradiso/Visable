# Live law grounding citation hardening (2026-05)

## Problem observed

Production showed the H-1 summer-course source panel with raw/low-trust states:

- `SOURCE_UNAVAILABLE`
- `LAW_API_BAD_RESPONSE`
- `CITATION_VERIFICATION_NOT_WIRED`
- a weak source-limited opening that began by saying Paradiso could not confirm the answer.

That combination made a cautious answer look unsupported and unfinished.

## Root causes investigated

The Open Law API adapter previously assumed a narrow JSON response and treated malformed or unexpected payloads generically. Citation verification also stayed in an extracted-only/not-wired state even when normalized law evidence existed. The UI then surfaced those raw internal states too prominently.

## Law API response parser hardening

The adapter now distinguishes safe response shapes and maps failures to stable typed errors:

- JSON object root;
- JSON list root;
- nested result/list structures;
- single result objects;
- empty responses as `law_api_no_results`;
- official error payloads as `law_api_official_error`;
- XML responses by converting them to a normalized object walk;
- HTML/text responses as unsupported bad responses without exposing body text.

Raw response bodies are never passed to the LLM or debug output. Source URLs are sanitized so OC/key query parameters are removed.

## Citation verification wiring

Normalized law evidence now creates citation metadata with:

- `source_type: law`;
- law name and reference/article field when available;
- query and retrieval status;
- sanitized source URL;
- verification status.

Citation verification states are now:

- `verified_law_evidence`;
- `law_evidence_present_unverified`;
- `law_evidence_unavailable`;
- `law_api_unavailable`;
- `citation_verification_not_applicable`.

`CITATION_VERIFICATION_NOT_WIRED` is not used for normalized law evidence and should not be shown as default user-facing source-panel text.

## Source panel trust-language changes

The source panel distinguishes:

- supporting legal source retrieved;
- no direct legal source found for the specific scenario;
- source lookup unavailable in deployment;
- unsupported API response format;
- official API error;
- timeout/network lookup failure.

Raw internal codes remain available only in collapsed technical details.

## H-1 answer conclusion policy

For H-1 credit-bearing or degree-related university summer-course questions, source-limited answers should begin with a practical safety posture:

> Paradiso cannot verify that an H-1 holder may take a credit-bearing or degree-related university summer course in Korea. Treat this as requiring official confirmation before enrollment or payment.

Then explain that the key issue is whether immigration treats the course as within H-1's permitted activity scope or as activities outside the scope of status. Casual/non-credit activities may be assessed differently, but official confirmation is required.

## Debug endpoint fields

`/api/debug/law-grounding` now reports safe diagnostic fields such as:

- planned queries;
- attempted targets;
- normalized evidence count;
- error type;
- parser status;
- response shape hint;
- sanitized source URL;
- citation verification status.

It does not expose OC/key values, raw response bodies, or raw URLs containing credentials.

## Smoke commands

Useful smoke commands:

```bash
python3 -m py_compile scripts/smoke_ai_live_quality.py
python3 scripts/smoke_ai_live_quality.py --help
node scripts/check_i18n.js
node scripts/check_ai_shell_semantics.js
python3 -m pytest backend/tests/test_law_tools.py -q
```

The live smoke reports law grounding status, law error type, parser status, response shape hint, citation status, law evidence count, source-panel status, risky phrases, raw-code UI leak checks, and H-1 first-line quality warnings. External law API unavailability should not fail CI; tests mock official response shapes.

## Tests added

Tests cover JSON list/single/nested responses, XML response normalization, official error mapping, HTML/text bad-response mapping without body leaks, empty results, sanitized URLs, citation verification from normalized evidence, H-1 query planning, and source-panel static semantics.

## Known limitations

- Open Law API may still not provide a scenario-specific answer for H-1 study questions.
- Law evidence supports context, not final adjudication.
- Manual absence remains visible.
- Official confirmation remains required.

## Safety note

Paradiso cannot determine final eligibility, permission, or required documents. Users must confirm case-specific outcomes with 1345, HiKorea, or the competent immigration office.
