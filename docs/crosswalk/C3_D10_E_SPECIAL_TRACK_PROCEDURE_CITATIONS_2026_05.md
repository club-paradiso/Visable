# C-3/D-10/E-series Special-track Procedure Citations - 2026.5

## Purpose

This document expands the high-risk procedure citation layer for C-3, D-10, and E-series special tracks.

It is intentionally bundled with the employment-reporting helper work in this PR because the E-series records, especially E-7 and H-2-adjacent employment pathways, depend on occupation and industry classification context.

This is still a source/crosswalk layer. It does not directly patch `visa_data.json` or verification metadata.

## Source baseline

- Manual: `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- Physical PDF page numbering is used.
- Classification context: KSCO8 for occupation and KSIC11 for industry.

## Summary matrix

| Status/group | Procedure/use | Manual citation | Scope | Patch readiness |
| --- | --- | --- | --- | --- |
| C-3 | short-stay/change boundary | stay manual pp. 209, 347 | C-3 appears as a limited source status for specific change cases and as an exclusion in some long-stay changes | DO_NOT_GENERALIZE |
| D-10 | change to E-series | stay manual pp. 198, 202, 208 | D-10 can support change to E-3/E-4/E-5/E-6 when the receiving status requirements are met | NEEDS_TARGET_STATUS_REVIEW |
| D-10 | Top-Tier path | stay manual pp. 671-672 | Top-Tier D-10 path is limited to 최우수인재 context | SUBTRACK_SCOPE_LIMITED |
| E-7 general | status-change and extension | stay manual pp. 213, 223, 226, 229 | E-7 general rules, job-code classification, employer ratio, and general extension documents | READY_FOR_FIELD_REVIEW |
| E-7-3/E-7-4/E-7-S/E-7-T | special-track separation | stay manual pp. 233, 293-294, 298-312, 675 | separate special tracks; do not merge with general E-7 record | SUBCODE_SCOPE_LIMITED |
| E-8 | seasonal-worker registration/workplace | stay manual p. 324 | E-8 foreigner registration and workplace-change context | READY_FOR_FIELD_REVIEW |
| E-9 | employment-permit context | stay manual pp. 229, 566 | E-9 appears in employer-ratio exclusions and health-status confirmation context | NEEDS_E9_SECTION_EXTRACTION |
| E-10 | seafarer activity/change/reporting | stay manual pp. 336, 339 | E-10 seafarer scope and employment-change reporting | READY_FOR_FIELD_REVIEW |
| Top-Tier | F-2/E-7/D-10/F-5 path | stay manual pp. 670-675, 683 | special high-talent pathway with D-10, E-7-T, F-2-T/F-5-T logic | SUBTRACK_SCOPE_LIMITED |
| K-STAR | F-2-7S/F-5-S1/F-2-71/F-5-S2 | stay manual pp. 749-758, 761, 765, 768 | special science/technology talent track; includes residence, permanent residence, family, score tables | SUBTRACK_SCOPE_LIMITED |

## Detailed notes

### C-3

C-3 should not be handled as a generic bridge to long-term residence. Page 209 shows a limited change-to-E-6 context for B-1/B-2/C-3 entrants when unavoidable or necessary for national interest. Page 347 shows C-3 as an exclusion in a D-4-3-related family change context.

Patch rule: do not use C-3 mentions as a universal change-of-status rule.

### D-10

D-10 appears repeatedly as a source status for change to professional E-series categories. Pages 198, 202, and 208 show D-10 or D-2 to E-4/E-5/E-6 change contexts when the receiving status requirements are met.

Patch rule: D-10 records should point to the target E-series status and must not imply a universal employment permission.

### E-7 general and special tracks

Page 213 establishes E-7 subcode taxonomy and explicitly connects E-7 job codes to Korean Standard Classification of Occupations. Page 226 provides the general E-7 extension document list. Page 229 explains employer ratio and wage/employer review logic. Page 233 separates E-7-3, E-7-4, E-7-S, E-7-Y, and E-7-T.

E-7-4 pages 298-312 must be kept separate from general E-7. E-7-S pages 293-294 and E-7-T page 675 are also special tracks.

Patch rule: no generic E-7 patch may absorb E-7-4, E-7-S, E-7-Y, or E-7-T without explicit subtrack labels.

### E-8/E-9/E-10

E-8 p. 324 supports seasonal-worker registration and workplace-change context. E-10 pp. 336 and 339 support seafarer scope and employment-change reporting. E-9 requires a separate extraction pass because this citation layer only anchors cross-status references and health-status confirmation pages.

### Top-Tier and K-STAR

Top-Tier pp. 670-675 and 683 support special high-talent D-10/E-7/F-2/F-5 logic. K-STAR pp. 749-758, 761, 765, and 768 support science/technology talent F-2/F-5/family routes and score tables.

Patch rule: these special tracks must stay out of general D-10/E-7/F-2/F-5 data until explicitly mapped.

## Data-patch boundary

These citations may support future field review, but they do not automatically authorize data correction.

Future patch PRs must:

1. keep C-3 limits narrow,
2. map D-10 to the target E-series status,
3. keep E-7 special tracks separate,
4. use KSCO8/KSIC11 context for occupation/industry-related fields,
5. avoid metadata promotion until the metadata gate is satisfied.
