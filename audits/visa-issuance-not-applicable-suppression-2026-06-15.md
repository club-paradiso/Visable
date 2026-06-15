# 사증발급 비대상 자격에서 '사증발급' 노출 차단 — 전수조사 (2026-06-15)

## 문제
각 체류자격 검색 결과의 **[절차별 안내]** 영역에서, 사증발급이 적용되지 않는
자격에도 **사증발급** 절차(탭/별도 섹션)가 노출되는 오류.

### 원인
- `visa_data.json` 의 거의 모든 레코드가 레거시 `newReq` 텍스트(및
  `initialReqDocs`/`newReqDocs`)를 보유 → `getProcedure()` 의 `legacyAvailable`
  이 항상 참이 되어 **모든 자격**에서 사증발급 탭이 켜짐.
- 사증면제(B-1·B-2)·사증발급 비대상(H-2) 자격도 동일하게 사증발급 탭이 떴고,
  탭 내부 카드는 "해당 없음"만 보여 줘 혼란을 유발.
- 영주(F-5)는 사증발급 탭을 숨기도록(`isSuppressedProcedureForStatus`) 되어
  있었으나, 탭이 없으면 동작하는 **별도 섹션 fallback**
  (`renderStandaloneVisaIssuanceSection`)이 [절차별 안내] 바로 아래에 사증발급
  섹션을 다시 렌더링 → 사증발급이 누락 차단 의도와 반대로 노출.

## 전수조사 결과 (42개 레코드)
판정 근거: 보호 데이터 `data/visa_issuance_records.json` 의 `issuanceModes.type`.

| 구분 | 자격 | 근거 |
|---|---|---|
| **사증발급 숨김** | B-1, B-2 | `visa_exempt` (사증면제 입국) |
| **사증발급 숨김** | H-2 | `not_applicable` (사증발급 비대상) |
| **사증발급 숨김** | F-5 | 영주 — 국내 체류자격 변경으로 취득(영주 사증 없음) |
| 사증발급 유지 | D·E·F(F-4 제외)·G·H-1·A·C·K-STAR·REGION-S·YOUTH-STAY 등 38종 | 실제 신청 경로(`mixed`/`consular_discretion`/`visa_issuance_confirmation`) 보유 |
| 별도 처리 | F-4 | 재외동포 전용 route guide 유지(기존 그대로) |

## 수정 (렌더러 전용 — 보호 데이터 미변경)
`index.html` 한 파일, JS 3곳:

1. **`isVisaIssuanceNotApplicable(v)` 신규** — `issuanceModes` 가 전부
   `visa_exempt`/`not_applicable` 이거나 코드가 F-5 일 때 참. 실제 신청 경로가
   하나라도 있으면 거짓(기존 노출 유지).
2. **`isSuppressedProcedureForStatus`** — 사증발급 탭 숨김 판정을 위 헬퍼에
   위임(F-5 단독 → F-5·B-1·B-2·H-2). 다른 절차 탭(연장·변경·등록 등)에는 영향
   없음.
3. **`renderVisaIssuanceSection`** 진입부 가드 — 비대상 자격이면 embedded(탭)·
   standalone(별도 섹션) 양쪽 모두 빈 문자열 반환 → fallback 누수까지 차단.

## 보존/제약
- 보호 파일(`visa_data.json`, `backend/data/visas.json`, `doc_master.json`),
  `data/visa_issuance_records.json`, `procedure_evidence_bindings.json` **미변경**.
- 법령/요건/문서 추가·삭제 없음. 면책·주의·출처 문구 변경 없음.
- 서브코드를 부모로 평탄화하지 않음. 사증발급↔체류 절차 혼합 없음.

## 검증
```
node scripts/check_visa_issuance_ui.mjs        → 2233 checks, 0 failures
node scripts/check_f4_route_guide.mjs          → 83 checks, 0 failures
node scripts/check_static_visa_result_cards.js → OK
node scripts/validate_visa_issuance_enrichment.js → 409 passed, 0 failed
node scripts/check_index_hardcoded_text.mjs    → OK
node scripts/check_i18n_coverage.mjs           → OK (1039 keys)
node scripts/check_placeholder_suppression.js  → 19 passed, 0 failed
node scripts/smoke_static_i18n.mjs             → OK (inline scripts parse)
```
실제 함수 추출 실행으로 분류 확인: 사증발급 숨김 = {B-1, B-2, H-2, F-5},
나머지 38종 유지, 다른 절차 탭 영향 없음.
