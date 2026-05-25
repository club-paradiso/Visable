# Visa/Stay Status Coverage Audit - 2026.5

## Scope

This audit compares `visa_data.json` against the legal top-level stay-status framework and the 2026.5 immigration manuals.

This is an audit-only artifact. It does not edit `visa_data.json`, does not promote `verified=true`, and does not create new legal-content records.

## Source basis

- 출입국관리법 시행령 별표 1 / 별표 1의2 체류자격 체계
- 2026.5 체류민원 안내매뉴얼 목차 및 체류자격별 섹션
- 2026.5 사증발급 안내매뉴얼
- HiKorea 체류자격별 안내메뉴얼 및 출입국관련 법령지침정보

## Canonical manual files checked in repository

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`: present
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`: present
- `docs/source-manuals/2026-05/체류민원 안내매뉴얼_260521.pdf`: not found
- `docs/source-manuals/2026-05/사증발급 안내매뉴얼_260521.pdf`: not found

## Legal top-level stay-status coverage

- Expected legal top-level statuses: 37
- Covered in `visa_data.json`: 37
- Missing legal top-level statuses: 0

No missing legal top-level stay-status code was detected against the expected legal list.

### Extra top-level records requiring classification review

- `COM-1`
- `D-4-2K`
- `FAQ-1`
- `FAQ-2`
- `FAQ-3`
- `FAQ-4`
- `K-STAR`
- `NHIS-1`
- `OVS-1`
- `REGION-S`
- `RF-1`
- `VW-1`

## 2026.5 manual policy/track section coverage

- **외국국적동포 관련**: covered
  - coverage_state: `full`
  - covered: `True`
  - partial_covered: `False`
  - Hits: C-3-8, F-1, H-2, F-4, F-5, 외국국적동포, 재외동포, 방문취업
- **지역특화형비자**: not covered - needs review
  - coverage_state: `missing`
  - covered: `False`
  - partial_covered: `False`
  - Terms not found: 지역특화형, F-2-R, F-4-R
- **국내 성장 기반 외국인 청소년 취업·정주 체류제도**: covered
  - coverage_state: `full`
  - covered: `True`
  - partial_covered: `False`
  - Hits: 국내 성장, 외국인 청소년, 청소년
- **탑티어(Top-Tier) 비자**: partial coverage - needs review
  - coverage_state: `partial`
  - covered: `False`
  - partial_covered: `True`
  - Hits: Top-Tier, D-10-T, E-7-T, F-2-T, F-5-T
  - Terms not found: 탑티어
- **광역형 비자 시범사업**: covered
  - coverage_state: `full`
  - covered: `True`
  - partial_covered: `False`
  - Hits: 광역형, 시범사업
- **K-STAR 비자트랙 제도**: partial coverage - needs review
  - coverage_state: `partial`
  - covered: `False`
  - partial_covered: `True`
  - Hits: K-STAR, 비자트랙
  - Terms not found: KSTAR

## F-1-6 diagnosis

- Top-level `F-1-6` record exists: `False`
- `subCodes[]` parents: `none`
- Text-hit records: `F-1, SCN-4`

Interpretation: `F-1-6` should not be treated as a missing independent top-level legal stay status unless a source explicitly defines it that way. It should be handled as a searchable detail code, subcode, alias, or scenario reference resolving to the relevant parent/scenario card.

## Detail-code alias candidates

- Detail code candidates not represented as top-level records: 122
- These are candidates for a future search resolver patch, not automatic new `visa_data.json` records.

- `B-1-1` - subcode parents: B-1; text-hit records: B-1
- `B-1-2` - subcode parents: B-1; text-hit records: B-1
- `B-2-1` - subcode parents: B-2; text-hit records: B-2, VW-1
- `B-2-2` - subcode parents: B-2; text-hit records: B-2, VW-1
- `C-3-1` - subcode parents: C-3; text-hit records: C-3
- `C-3-10` - subcode parents: C-3; text-hit records: C-3
- `C-3-2` - subcode parents: C-3; text-hit records: C-3
- `C-3-3` - subcode parents: C-3; text-hit records: C-3
- `C-3-4` - subcode parents: C-3; text-hit records: C-3, D-4-2K
- `C-3-5` - subcode parents: C-3; text-hit records: C-3
- `C-3-6` - subcode parents: C-3; text-hit records: C-3
- `C-3-8` - subcode parents: C-3; text-hit records: C-3
- `C-3-9` - subcode parents: C-3; text-hit records: C-3
- `D-1-00` - subcode parents: D-1; text-hit records: D-1
- `D-10-1` - subcode parents: D-10; text-hit records: D-10
- `D-10-2` - subcode parents: D-10; text-hit records: D-10
- `D-10-3` - subcode parents: D-10; text-hit records: D-10
- `D-10-T` - subcode parents: D-10; text-hit records: D-10
- `D-2-1` - subcode parents: D-2; text-hit records: D-2
- `D-2-2` - subcode parents: D-2; text-hit records: D-2
- `D-2-3` - subcode parents: D-2; text-hit records: D-2
- `D-2-4` - subcode parents: D-2; text-hit records: D-2
- `D-2-5` - subcode parents: D-2; text-hit records: D-2
- `D-2-6` - subcode parents: D-2; text-hit records: D-2
- `D-2-7` - subcode parents: D-2; text-hit records: D-2
- `D-2-8` - subcode parents: D-2; text-hit records: D-2
- `D-2-R` - subcode parents: D-2; text-hit records: D-2
- `D-3-11` - subcode parents: D-3; text-hit records: D-3
- `D-3-12` - subcode parents: D-3; text-hit records: D-3
- `D-3-13` - subcode parents: D-3; text-hit records: D-3
- `D-4-1` - subcode parents: D-4; text-hit records: D-2, D-4
- `D-4-2` - subcode parents: D-4; text-hit records: D-4
- `D-4-3` - subcode parents: D-4; text-hit records: D-4
- `D-4-5` - subcode parents: D-4; text-hit records: D-4
- `D-4-6` - subcode parents: D-4; text-hit records: D-4
- `D-4-7` - subcode parents: D-4; text-hit records: D-2, D-4
- `D-7-1` - subcode parents: D-7; text-hit records: D-7
- `D-7-2` - subcode parents: D-7; text-hit records: D-7
- `D-7-91` - subcode parents: D-7; text-hit records: D-7
- `D-7-92` - subcode parents: D-7; text-hit records: D-7
- `D-8-1` - subcode parents: D-8; text-hit records: D-8
- `D-8-2` - subcode parents: D-8; text-hit records: D-8
- `D-8-3` - subcode parents: D-8; text-hit records: D-8
- `D-8-4` - subcode parents: D-8; text-hit records: D-8
- `D-8-91` - subcode parents: D-8; text-hit records: D-8
- `D-9-1` - subcode parents: D-9; text-hit records: D-9
- `D-9-2` - subcode parents: D-9; text-hit records: D-9
- `D-9-3` - subcode parents: D-9; text-hit records: D-9
- `D-9-4` - subcode parents: D-9; text-hit records: D-9
- `E-10-1` - subcode parents: E-10; text-hit records: E-10
- `E-10-2` - subcode parents: E-10; text-hit records: E-10
- `E-10-3` - subcode parents: E-10; text-hit records: E-10
- `E-2-1` - subcode parents: E-2; text-hit records: E-2
- `E-2-2` - subcode parents: E-2; text-hit records: E-2
- `E-2-91` - subcode parents: E-2; text-hit records: E-2
- `E-6-1` - subcode parents: E-6; text-hit records: E-6
- `E-6-2` - subcode parents: E-6; text-hit records: E-6, OVS-1
- `E-6-3` - subcode parents: E-6; text-hit records: E-6
- `E-7-1` - subcode parents: E-7; text-hit records: D-4-2K, E-7
- `E-7-2` - subcode parents: E-7; text-hit records: D-4-2K, E-7
- `E-7-3` - subcode parents: E-7; text-hit records: E-7
- `E-7-4` - subcode parents: E-7; text-hit records: E-7
- `E-7-91` - subcode parents: E-7; text-hit records: E-7
- `E-7-S` - subcode parents: E-7; text-hit records: E-7
- `E-7-T` - subcode parents: E-7; text-hit records: E-7
- `E-7-Y` - subcode parents: E-7; text-hit records: E-7
- `E-9-1` - subcode parents: E-9; text-hit records: E-9
- `E-9-10` - subcode parents: E-9; text-hit records: E-9
- `E-9-2` - subcode parents: E-9; text-hit records: E-9
- `E-9-3` - subcode parents: E-9; text-hit records: E-9
- `E-9-4` - subcode parents: E-9; text-hit records: E-9
- `E-9-5` - subcode parents: E-9; text-hit records: E-9
- `E-9-9` - subcode parents: E-9; text-hit records: E-9
- `E-9-JS` - subcode parents: E-9; text-hit records: E-9
- `E-9-R` - subcode parents: E-9; text-hit records: E-9
- `F-1-13` - subcode parents: F-1; text-hit records: D-4, F-1
- `F-1-21` - subcode parents: F-1; text-hit records: F-1
- `F-1-22` - subcode parents: F-1; text-hit records: F-1
- `F-1-23` - subcode parents: F-1; text-hit records: F-1
- `F-1-24` - subcode parents: F-1; text-hit records: F-1
- ... 42 more candidates omitted from markdown; see JSON artifact.

## Recommended next step

Create a separate search-resolver PR so exact detail-code queries such as `F-1-6`, `F-2-7`, or `E-7-4` resolve to their parent/subcode/scenario records instead of returning an empty result.

## Guardrails

- No `visa_data.json` edits.
- No backend edits.
- No automatic legal-content creation.
- No source verification promotion.
- No deletion of scenario/helper records.

