# Document Term and Fee Normalization Audit - 2026.5

## Scope

This patch audits all `visa_data.json` records and conservatively normalizes common document terms and fee-display metadata.

## Source/API status

External law/public-data runtime integration is not used by this patch; repository-local manual/data artifacts are used conservatively.

## Manual files checked

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`: present
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`: present
- `docs/source-manuals/2026-05/체류민원 안내매뉴얼_260521.pdf`: not found
- `docs/source-manuals/2026-05/사증발급 안내매뉴얼_260521.pdf`: not found

## Summary

- Records checked: `58`
- Records touched: `24`
- Normalized document terms: `36`
- Split combined document items: `0`
- Fee metadata records updated: `0`
- Scenario/help shadow records synced: `0`

## Canonical examples

- `신청서`, `통합신청서`, `신청서(별지 제34호 서식)` -> `통합신청서(별지 제34호 서식)`
- `여권` -> `여권 원본 및 인적사항면 사본`
- `표준규격사진 1매` -> `표준규격사진 1매(3.5×4.5cm, 최근 6개월)`
- `수수료` -> `수수료(절차별 정부수입인지/카드 발급 수수료 확인)`

## Fee display baseline

- 외국인등록: 외국인등록증 발급 수수료 35,000원
- 체류기간 연장: 정부수입인지 60,000원
- 체류자격 변경: 정부수입인지 100,000원, 등록증 발급 필요 시 35,000원 별도 가능
- 체류자격 부여: 정부수입인지 80,000원, 외국인등록 대상자는 등록증 발급 수수료 35,000원 별도 가능
- 사증발급: 국적, 사증 종류, 재외공관 기준에 따라 달라짐

## Guardrails

- No new visa/status records.
- No record deletion.
- No `verified=true` promotion.
- No backend code changes.
- No external law API call.
- Fee metadata is display metadata and keeps final-confirmation warning.

## Manual QA

- [ ] Search `F-6`.
- [ ] Confirm document terms are consistent across required/common/procedure sections.
- [ ] Confirm the active procedure shows a fee notice.
- [ ] Check `외국인등록` fee display.
- [ ] Check `체류기간 연장` fee display.
- [ ] Check `체류자격 변경` fee display.
- [ ] Search `F-1-6`, `E-7-4`, `F-2-7` to confirm prior alias behavior still works.

