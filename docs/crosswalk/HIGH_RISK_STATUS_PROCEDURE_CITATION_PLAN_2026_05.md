# High-risk Status Procedure Citation Plan - 2026.5

## Purpose

This document prepares the next crosswalk expansion after the common procedure citations and the first status-specific citation seed.

The goal is to prioritize high-risk statuses before any scoped data correction. These statuses have higher user impact, sub-code complexity, or known gaps in structured procedure/document data.

## Scope

Documentation/crosswalk only.

This plan does not change production data, verification metadata, frontend behavior, or runtime AI/law-grounding behavior.

## Priority groups

| Priority | Status group | Reason | Next citation work |
| --- | --- | --- | --- |
| 1 | G-1 and G-1 subcodes | humanitarian/refugee-related stay risk and travel/re-entry uncertainty | identify extension, change, registration, re-entry/travel-risk citations |
| 2 | F-series | long-term residence, family, overseas Korean, and permanent-residence complexity | map extension/change/registration pages by status and sub-code |
| 3 | H-1/H-2 | working-holiday and visiting-employment procedures affect many users | map registration, extension, workplace/reporting, and online-report examples |
| 4 | C-3 | short-stay boundary and change/extension limits create frequent user confusion | map extension/change availability and prohibited generalizations |
| 5 | D-10 | job-seeking and transition cases are high-risk for status change | map extension and change pages with sub-route notes |
| 6 | E-series special tracks | employment conditions vary heavily by status and sub-track | separate E-7 general, E-7-4, E-7-S, E-7-T, E-8, E-9, E-10 |
| 7 | Regional/Jeju/special programs | local and program-specific requirements should not leak into general status records | map regional visa, broad-area pilot visa, Jeju/scenario records, Top-Tier, K-STAR |

## Required fields for each future status citation

Each future record should include:

- status code and sub-code scope,
- procedure key,
- manual source ID,
- exact PDF page or page range,
- law article anchor where applicable,
- target field placeholder,
- condition scope,
- conflict status,
- patch readiness label,
- explicit note preventing over-generalization.

## Patch-readiness rule

No status becomes ready for data patching just because a page exists. The page must directly support the exact target field, and conditional or sub-code-specific requirements must remain scoped.

## Recommended follow-up PR

`docs: expand G-1/F/H high-risk procedure citations`

Start with G-1, F-series, and H-1/H-2 because the user-facing risk is highest and existing structured data is likely weakest.
