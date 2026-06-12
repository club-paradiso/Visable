# Source Lens Enrichment Report

Generated: 2026-06-12

## Scope

This first PR adds a separate visa issuance and evidence layer, not a full all-status manual extraction. It covers priority status searches for: D-2, D-4, D-10, E-7, E-8, E-9, F-1, F-2, F-4, F-6, G-1, H-2, C-3, B-1, B-2.

## Source Lens Counts

All procedure rows before: {'unavailable': 208, 'limited': 58, 'contextual': 50, 'source_confirmed': 20}

All procedure rows after: {'not_applicable': 3, 'limited': 90, 'contextual': 47, 'unavailable': 169, 'source_confirmed': 27}

Parent `visa_issuance` rows before: {'unavailable': 39, 'contextual': 3}

Parent `visa_issuance` rows after: {'not_applicable': 3, 'source_confirmed': 7, 'limited': 32}

Priority `visa_issuance` rows before: {'unavailable': 13, 'contextual': 2}

Priority `visa_issuance` rows after: {'not_applicable': 3, 'source_confirmed': 7, 'limited': 5}

Changed matrix rows: 42

## Priority Coverage

Source-confirmed from local manual page refs: D-2, D-4, D-10, E-7, E-8, F-6, C-3

Not applicable / not shown as an application checklist: H-2, B-1, B-2

Still limited with explanation: E-9, F-1, F-2, F-4, G-1

## Remaining Limited Priority Items

- `E-9`: 공식 매뉴얼 위치는 확인했지만 EPS·송출국 절차와 세부 서류 구조화가 이번 PR에서 완료되지 않았습니다.
- `F-1`: 방문동거는 대상 범위가 넓어 세부 대상별 공식 서류 구조화가 아직 완료되지 않았습니다.
- `F-2`: 거주(F-2)는 세부 유형별 요건 차이가 커서 유형 선택 전 확정 안내로 표시하지 않습니다.
- `F-4`: 외국국적동포 하위 매뉴얼과 2026년 제도 변경 확인이 필요한 항목이라 제한 표시를 유지합니다.
- `G-1`: G-1은 세부 사유가 다양해 사유별 공식 서류 구조화가 필요합니다.

## Important Limits Kept Intentionally

- Timing, fees, reservation method, and channel details remain unconfirmed unless a specific official source binding supports them.
- F-4 and H-2 remain sensitive because the outer manual points to the foreign-national Korean submanual and 2026 policy changes.
- Official web overlays are seeded but not promoted into user guidance until manual verification is complete.

## Follow-up PR Slices

1. Complete manual extraction for remaining parent visa issuance records.
2. Add official web overlays for selected countries/posts from verified MOFA/mission/visa portal pages.
3. Add country/post selector behavior once confirmed overlay records exist.
4. Expand exact-code browser regression tests for D-2, E-7, F-6, and B-2/B-1 route separation.
5. Repair or separately scope the backend test harness mismatch that currently blocks `scripts/check_repo.sh`.
