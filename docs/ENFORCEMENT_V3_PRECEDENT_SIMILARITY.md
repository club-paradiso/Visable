# Enforcement Intelligence v3: Precedent Similarity

## Scope

`SimilarCaseReference.similarityScore` is a deterministic **retrieval relevance heuristic**. It is not a probability that the current case will receive the same disposition, monetary amount, or administrative treatment as the cited precedent.

Only citation-grade official precedent bodies can become similar-case references. Search/list metadata alone remains ineligible.

## Signals

The current score is intentionally conservative and uses only facts that can be compared between the structured current case and the bounded public body text:

- same or closely related legal issue: up to 0.50;
- exact status-of-stay code explicitly present in the public body: up to 0.20;
- comparable violation-duration bucket when the body explicitly states a duration: up to 0.15;
- comparable prior-violation/first-offense signal when explicitly stated: up to 0.10;
- voluntary-disclosure signal when explicitly stated: up to 0.05.

Missing information receives no similarity credit and is not silently treated as a match. Explicitly different status-of-stay, duration bucket, or prior-violation facts are recorded in `differingFactors`.

## Retrieval budget

The enforcement path defaults to two returned similar cases and caps the public candidate pool at three. Candidate body/detail requests are issued concurrently after one list search. Each official-source request remains governed by the existing enforcement-specific bounded grounding timeout.

This avoids the old behavior where `max_cases` was effectively hard-capped to one while also avoiding sequential N-times latency growth.

## Ranking and determinism

Verified body results are ranked by descending similarity score. Stable similar-case ID is the deterministic tie-breaker, so concurrent request completion order cannot change output order.

## Safety boundary

The score must not be:

- converted into a numeric outcome probability;
- described as a prediction confidence percentage;
- used as proof that two cases are legally identical;
- used to override the deterministic statutory baseline;
- populated for list-only, synthetic, fixture, demo, mock, or non-official records.

Every evidence pack containing scored similar cases includes a public limitation stating that the score is a search-relevance indicator, not an outcome probability.
