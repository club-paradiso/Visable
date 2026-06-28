# Generalized law grounding and article verification (2026-06)

## Scope

This change makes legal grounding issue-driven rather than E-7-specific. It applies the same bounded search, exact-article verification, evidence classification, and safe-degradation rules across immigration status families, nationality, refugee, KIIP, registration, status changes, outside-status activity, re-entry, and penalty-risk questions.

No external MCP or hosted proxy was added as a production dependency. The existing official National Law Information Center API remains the runtime source.

## Retrieval and verification contract

`build_law_search_queries()` produces a capped list of discrete queries. The `/api/ask` path executes each query independently and deduplicates normalized results by source family, law identity, serial/MST, and article identity. The compatibility `build_law_search_query()` remains diagnostic-only.

An explicit citation is `verified` only when all of the following hold:

1. The cited law is found by name.
2. A law ID or MST can be resolved.
3. The official detail endpoint returns the cited article.
4. The normalized law name and normalized article number both match.
5. The article body is non-empty.

A list-search hit alone never verifies an article. Missing articles, empty detail responses, malformed HTML responses, upstream errors, and timeouts are represented by lower states such as `source_linked_unverified`, `extracted_only`, or `failed_verification`. Only bounded official excerpts enter the evidence pack.

## Evidence-grade invariants

`enforce_source_confidence_invariants()` deterministically prevents `source_confirmed`, `high`, and `requires_official_confirmation=false` when direct authority is absent, official lookup failed, an explicit citation is unverified, or structured evidence does not match the question procedure.

Structured manual requirements are direct evidence only when status/sub-status scope and procedure type match. The `/api/ask` path does not promote any structured record when it cannot classify the requested procedure. Related or background material remains supplemental and cannot raise confidence.

The response metadata, evidence pack, answer-quality status, and UI-facing source summaries are synchronized after invariant enforcement.

## Precedent handling

Official `law.go.kr` absolute URLs and safe `/DRF/lawService.do?...` relative URLs are normalized. Relative URLs become `https://www.law.go.kr/...`. Script/data schemes, protocol-relative URLs, non-`law.go.kr` hosts, control characters, traversal, and abnormal paths are rejected.

List results are deduplicated by source ID and by case number/court/date. List metadata does not synthesize holdings. Bounded holding, summary, reference-article, and disposition fields are returned only by the official detail path when those fields are present upstream.

## Security and deployment

- `LAW_API_OC`, `LAW_API_KEY`, and OC query values are stripped from public URLs and never returned in API metadata.
- Existing disclaimers, uncertainty copy, and citation guardrails remain in place.
- No secrets, GitHub Pages settings, Railway settings, deployment workflow, model, or provider configuration changed.
- Rollback is a normal revert of this branch's four logical commits; no data migration is required.

## Verification performed

- Related Python suites: passed.
- Offline selected pytest regression set: 611 passed, 61 subtests passed.
- Targeted post-invariant suite: passed.
- `npm run test:legal-search`: 210 pure checks and 55 DOM checks passed.
- `bash scripts/check_repo.sh`: all 14 stages passed; AI golden eval 50/50.
- Secret-value scan: performed separately before publication.

One broader optional planner suite contains a pre-existing expectation mismatch in `test_routine_extension_or_route_question_does_not_plan_precedent`: the baseline planner includes `administrative_appeal` for that route. The modified grounding, confidence, precedent, UI, and test files do not implement that planner behavior.

## Residual risks

- Official upstream schemas can vary; malformed or partial responses intentionally downgrade instead of guessing.
- Article matching is exact after Korean article-number normalization, so an upstream response that omits article bodies cannot be verified even when the law list result is correct.
- Precedent detail availability depends on the official source exposing the requested bounded fields.
