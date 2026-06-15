# 공항 환승만(transit_only) 정확도 개선 — 순수환승(C-3-10) 반영

- 작업일: 2026-06-15
- 범위: 국적별 단기입국 경로 확인(short-stay checker)의 "방문 지역 = 공항 환승만"
  (`destination = transit_only`) 및 "목적 = 환승, 지역 미선택" 경로
- 원칙(CLAUDE.md): 법령/요건을 임의로 만들지 않음. 로컬 공식 출처에 있는 내용만 사용.
  면책·불확실성·"입국 보장 아님" 경고를 약화하지 않음. 렌더러/리졸버 우선, 데이터는 surgical.

## 1. 문제 (Before)

기존 transit 분기는 국적·여권과 무관하게 단일 "공식 확인 필요" 답변만 제공했다.

```
환승 절차(순수환승 C-3-10 안내)  [needs_official_check]
- 입국심사를 거치지 않는 공항 환승은 별도 입국 경로가 필요하지 않은 경우가 많지만,
  국적·노선에 따라 환승 사증 또는 순수환승(C-3-10)이 필요할 수 있습니다.
```

→ "공항 환승만" 사용자가 (a) 사증이 필요한 국적인지, (b) 외교·관용여권 면제 대상인지,
(c) 그 밖의 국적은 무사증 통과인지 구분된 정확한 답을 받지 못했다.

## 2. 출처 (로컬 공식 자료에서 확인한 사실만 사용)

`docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt` (2026.5 사증발급 안내매뉴얼):

- **6. 순수환승 (C-3-10)** (라인 1542–1555)
  - 발급 대상: **시리아, 수단, 예멘, 이집트 일반여권 소지자** (대한민국 경유 제3국행)
  - **외교·관용여권 소지자는 순수환승(C-3-10) 사증 없이 환승 가능**
  - 제출: 사증발급신청서·여권·사진·수수료·**여행계획서(서식3)**
  - 발급 내용: **단수사증, 유효기간 3개월, 체류기간 0일**, 입국심사 목적 사용 불가
  - **환승구역 내 72시간 동안 임시 체재만 가능**
- 라인 1397: "대한민국을 경유하여 제3국으로 여행하려는 자 / 입국심사 목적 사용 불가"
- 라인 1085–1090: 출입국관리법 제7조 — 사증은 **'입국'** 시 필요. 입국심사를 거치지 않는
  환승구역 통과는 입국이 아님 → 그 밖의 국적은 원칙적으로 별도 대한민국 사증 불요.

확인 사항: 로컬 출처(visa 매뉴얼, `rule_1106_full.txt`, lawgokr 조문)에 **별도의 "환승관광
무사증/TWOV" 제도**는 정의되어 있지 않음 → 만들어내지 않음. (라인 1851의 "무사증환승"은
출입국기록 항목 언급일 뿐, 요건 정의 아님.)

## 3. 변경 (After)

### 데이터 (생성물은 직접 편집 금지 — fixture만 수정 후 재생성)
- `data/short-stay/fixtures/c3_fallback.json`: `transitRule` 노드 추가
  (code C-3-10, `visaRequiredNationalitiesKo`=[시리아,수단,예멘,이집트],
  `visaRequiredPassportScope`=ordinary, `diplomaticOfficialExempt`=true,
  validity/stayPeriod(0일)/transitAreaHours(72)/applicationDocsNote/notes/sourceRefs).
- `scripts/update_short_stay_rules.mjs`: `buildTransitRule()`가 국가명→ISO 해석하여
  `rules.rules.c3Fallback.transitRule`(+`visaRequiredIso2`=[SY,SD,YE,EG]) 생성.
- 재생성: `node scripts/update_short_stay_rules.mjs --from-fixtures`.
  `source_diff.json` 확인: **changedCountries: []** (국가 레코드 0건 변경 — surgical).

### 엔진/렌더러 (`assets/js/short-stay-checker.js`)
- transit 분기를 여권/목적 분기보다 **먼저** 평가(환승은 입국이 아니므로 입국용 로직과 분리).
- `resolveTransit()` 4분기:
  1. C-3-10 대상 + 일반/미상 여권 → `transit_visa_required` (순수환승 C-3-10 신청,
     유효 3개월·체류 0일·환승구역 72시간·입국 불가 명시)
  2. C-3-10 대상 + 외교·관용여권 → `transit_no_visa` (매뉴얼상 면제, 단 일반여권은 필요 명시)
  3. C-3-10 대상 + 특별/서비스 등 → `needs_official_check` (매뉴얼 미명시 → 단정 안 함)
  4. 그 밖의 국적 → `transit_no_visa` (입국심사 없는 환승은 원칙적으로 별도 사증 불요)
- 새 verdict tone `transit`(✈️) + 배지(`환승 사증 불요` / `순수환승 사증 필요`).
- 모든 분기에 "공항 밖으로 나가는 것은 환승이 아니라 입국" 경고 + 항공사·최종입국심사 경고 유지.
- "입국 보장" 식 표현 없음, 약한 표현("~로 보입니다") 없음.

## 4. 검증

- `node scripts/check_short_stay_rules.mjs` → **99 checks, 0 failures**
  (transitRule 스키마 + SY/EG/YE/JP/VN 시나리오 + 입국·환승 보장 표현 금지 회귀 포함).
- `node scripts/check_short_stay_freshness.mjs` → exit 0 (기존 제주 2022 고시 STALE 경고만; 무관).
- DOM 렌더 스모크(최소 스텁 + 실제 rules.json, open→submit→render):
  - 시리아/일반 → `ssc-verdict-visa` 📋 / "환승에도 순수환승(C-3-10) 사증이 필요합니다" / 배지 "순수환승 사증 필요"
  - 이집트/외교 → `ssc-verdict-transit` ✈️ / "사증 없이 공항 환승이 가능한 경우입니다" / 배지 "환승 사증 불요"
  - 일본/일반 → `ssc-verdict-transit` ✈️ / 동일(무사증 환승)
- `index.html` 변경 없음(체커는 외부 JS+rules.json 사용, 모달 호스트 기존 유지).

## 5. 남은 재확인(상시)

- 순수환승(C-3-10) 사증 대상국·여권범위는 2026.5 매뉴얼 기준. 매뉴얼 개정 시
  `c3_fallback.json`의 `transitRule.visaRequiredNationalitiesKo`만 갱신 후 재생성.
- 입국심사 없는 공항 환승의 무사증 통과는 출입국관리법 제7조('입국' 시 사증) 해석 기반의
  일반 안내이며, 노선·항공사 탑승 규정·최종 목적지(제3국) 입국요건은 별도 확인 필요(경고 유지).
