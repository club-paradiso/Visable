# G-1/F/H High-risk Procedure Citations - 2026.5

## Purpose

This document expands the high-risk status procedure citation layer for G-1, F-series, H-1, and H-2.

It is documentation/crosswalk work only. It does not change production visa data, verification metadata, frontend behavior, or runtime AI/law-grounding behavior.

## Source baseline

- Manual: `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- Physical PDF page numbering is used.
- These citations are page anchors for later field review, not automatic production-data patch authority.

## Summary matrix

| Status/group | Procedure/use | Manual citation | Scope | Patch readiness |
| --- | --- | --- | --- | --- |
| G-1 | activity scope / eligible persons | stay manual p. 498 | top-level G-1 scope and example categories | READY_FOR_FIELD_REVIEW |
| G-1 | employment outside status / refugee/humanitarian cases | stay manual pp. 499-503 | G-1 employment-permission context; refugee/humanitarian subcases | SUBCODE_SCOPE_LIMITED |
| F-1 | scope and common management | stay manual pp. 341-342 | F-1 general scope; activity exceptions and dependent-family contexts | READY_FOR_FIELD_REVIEW |
| F-1 | extension/change examples | stay manual pp. 344, 351 | status-change and extension examples, not universal F-1 list | NEEDS_SUBCASE_REVIEW |
| F-2 | change/extension and investment/long-term residence paths | stay manual pp. 367, 371, 375, 389 | F-2 is highly sub-route-specific; do not generalize across F-2 subcodes | SUBCODE_SCOPE_LIMITED |
| F-3 | dependent-family scope and extension | stay manual pp. 421, 425, 545 | F-3 general dependent-family and overseas-Korean-family subcases | NEEDS_SUBCASE_REVIEW |
| F-4 | overseas Korean manual block | stay manual pp. 518-545 | F-4 appears inside the dedicated overseas Korean section | NEEDS_SUBCASE_REVIEW |
| F-5 | permanent residence / overseas-Korean related sections | stay manual pp. 453, 518 | F-5 is not a simple stay-extension checklist; use subcase-specific review | SUBCODE_SCOPE_LIMITED |
| F-6 | status change for spouse of Korean national | stay manual p. 475 | F-6-1 change-of-status context; H-1 exclusion note included | READY_FOR_FIELD_REVIEW |
| H-1 | activity scope, extension, registration | stay manual pp. 514, 517 | working holiday / tourism-work restrictions and registration list | READY_FOR_FIELD_REVIEW |
| H-2 | stay permit and Korean-language proof context | stay manual p. 553 | H-2 stay permit context, especially H-2-7 and language-proof exemption | NEEDS_SUBCASE_REVIEW |
| H-2 | employment activity scope | stay manual pp. 555, 565 | H-2 industry/employment-scope rules; depends on industry classification | SUBCODE_AND_INDUSTRY_SCOPE_LIMITED |
| H-2 | health-status confirmation / registration context | stay manual p. 566 | E-9/E-10/H-2 health-status checklist and 90-day registration notice | READY_FOR_FIELD_REVIEW |

## Detailed notes

### G-1

- Page 498 defines G-1 as activities not covered by A-1 through F-6, H-1, or H-2 and lists example persons recognized by the Minister of Justice.
- Pages 499-503 cover employment permission contexts, including refugee applicants, humanitarian stay holders, and domestic-born minor children of humanitarian/refugee applicants.
- Do not treat G-1 as a single uniform checklist. G-1-5, G-1-6, G-1-12, G-1-99 and other subcases need separate source support before any data patch.

### F-series

- F-1 begins at p. 341 and includes general scope and activity limitations; later pages provide subcase examples.
- F-2 is especially fragmented. Pages 367, 371, 375, and 389 cover high-value investor, compliance education, real-estate investment, and long-term residence paths. These are not interchangeable.
- F-3 appears in general dependent-family context on p. 421 and family/extension examples on p. 425; overseas-Korean family management appears again around p. 545.
- F-4 and F-5 are partly governed through the dedicated overseas Korean section beginning around p. 518. Do not collapse F-4/F-5 into generic F-series handling.
- F-6 p. 475 supports the spouse-of-Korean change-of-status context and notes that H-1 holders are generally directed to the H-1 management guideline for F-6 change limits.

### H-series

- H-1 pp. 514 and 517 support working-holiday activity limits, extension context, re-entry guidance, and registration document examples.
- H-2 p. 553 supports stay-permit/language-proof context.
- H-2 pp. 555 and 565 support employment-activity scope and industry classification boundaries. This is directly connected to the separate KSCO/KSIC employment-reporting data work and should not be patched without industry-classification context.
- H-2 p. 566 includes E-9/E-10/H-2 health-status confirmation context and 90-day registration notice.

## Data-patch boundary

These citations may support future field review, but they do not themselves patch data.

Future data PRs must still:

1. preserve parity between `visa_data.json` and `backend/data/visas.json`,
2. keep subcode-specific requirements scoped,
3. keep industry-specific H-2 rules separate from generic H-2 stay procedures,
4. avoid using one F-series subcase as a universal F-series rule,
5. avoid metadata promotion until the metadata gate is satisfied.

## Recommended next PR

`docs: expand C-3/D-10/E-special-track procedure citations`

That follow-up should cover short-stay, job-seeking, and E-series special tracks separately before any scoped production data correction.
