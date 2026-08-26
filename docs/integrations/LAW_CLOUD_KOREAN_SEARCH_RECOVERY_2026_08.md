# Railway Korean Open Law search recovery — 2026-08

## Problem

The Railway backend had a valid configured Open Law credential and the public law-search proxy returned HTTP 200 with `ok=true`, but a Korean title search for `출입국관리법` returned `count=0`.

Historical runtime probes showed the same symptom for multiple unrelated Korean law names: the upstream API returned the same small successful-looking envelope with no candidates. This is consistent with a cloud-egress degradation where Korean `query=` searches can return a zero-result shell instead of normal rows.

## Recovery

Visable keeps the normal documented `query=` search as the primary path. Only when a Korean law search produces the zero-result condition does the backend use the documented mobile law-list dictionary filter (`mobileYn=Y`, ASCII `gana` group), fetch a bounded set of list pages, and perform conservative title matching locally.

The fallback:

- never changes successful normal searches;
- never hides transport, authorization, or parse failures;
- never exposes the Open Law credential;
- never fabricates law rows;
- returns the original no-result response if no credible title match is found;
- caches only bounded dictionary pages and stops early on empty groups.

## Runtime gate

The Railway live smoke now requires all of the following:

- backend `/health` is healthy;
- OpenRouter is configured;
- Open Law grounding is configured and active;
- `/api/legal/laws/search?q=출입국관리법` returns HTTP 200 and `ok=true`;
- the returned law-search `count` is greater than zero.

A deployment is not considered verified merely because the upstream HTTP status is 200; at least one usable law row must be returned.

This document intentionally contains no credential values.
