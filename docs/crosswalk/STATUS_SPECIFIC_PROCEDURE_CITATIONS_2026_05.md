# Status-specific Procedure Citations - 2026.5

## Purpose

This document adds the first status-specific citation layer after the common procedure citation map.

It uses currently verified local manual-grounding entries as seed records. The goal is to prove the citation pattern before expanding to all high-risk statuses.

This PR is still documentation/crosswalk only. It does not change production JSON data, verification metadata, frontend behavior, or AI answer generation.

## Seed status records

| Status | Procedure | Manual citation | Scope | Patch readiness |
| --- | --- | --- | --- | --- |
| D-2 유학 | 체류기간 연장허가 | 외국인체류 안내매뉴얼, PDF pp. 43-44 | top-level D-2 extension document list | READY_FOR_FIELD_REVIEW |
| D-4 일반연수 | 체류기간 연장허가 | 외국인체류 안내매뉴얼, PDF pp. 90-91 | D-4-1 and D-4-7 language-training sub-track only | SUBCODE_SCOPE_LIMITED |
| E-7 특정활동 | 체류기간 연장허가 | 외국인체류 안내매뉴얼, PDF p. 226 | general E-7 extension list only; special agreement/track sections excluded | READY_FOR_FIELD_REVIEW |

## Source interpretation

The page ranges above are absolute PDF page numbers in `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`.

They should not be generalized beyond their stated scope:

- D-4 pp. 90-91 covers only D-4-1 and D-4-7 language-training cases.
- E-7 p. 226 covers the general E-7 extension list, while later special-track subsections require separate citations.
- D-2 pp. 43-44 supports the D-2 extension list but does not automatically support unrelated D-series statuses.

## Required next extraction targets

| Priority | Target | Why |
| --- | --- | --- |
| 1 | G-1 and G-1 subcodes | High user risk and travel/re-entry/status ambiguity. |
| 2 | F-series | Residence/family/permanent-residence consequences are high-impact. |
| 3 | H-2 and H-1 | Employment and reporting requirements are procedure-heavy. |
| 4 | C-3 | Short-stay scenarios are common and easily overgeneralized. |
| 5 | D-10 and E-series special tracks | Job-seeking/employment logic depends on sub-track and occupation. |
| 6 | regional visa, broad-area pilot visa, Top-Tier, K-STAR | Newer policy tracks need precise source separation. |

## Data-patch boundary

These citations may support future data correction review, but they do not themselves patch data.

Future data PRs must still preserve parity between `visa_data.json` and `backend/data/visas.json`, must not remove review flags, and must not promote verification metadata until the metadata gate is satisfied.
