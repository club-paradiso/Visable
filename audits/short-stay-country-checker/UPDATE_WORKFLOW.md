# Short-stay data — update workflow

단기입국 체커 데이터(`data/short-stay/`)를 공식 출처 변경에 맞춰 갱신하는 절차.
**원칙(CLAUDE.md)**: 법령/요건을 임의로 만들지 않는다. fixture는 공식 출처 사본에서만
갱신하고, 면책·불확실성 경고는 약화·삭제하지 않는다.

## 데이터 구조
- `data/short-stay/fixtures/*.json` — **단일 진실 출처(SOT)**. 공식 사본을 사람이 정리.
  - `b1_visa_waiver.json` (사증면제협정 B-1), `b21_general_visa_free.json` (무사증 B-2-1),
    `keta_program.json` (K-ETA·한시 면제), `jeju_b22_notice.json` (제주 B-2-2 고시),
    `c3_fallback.json` (C-3 목적 매핑 + `transitRule` 순수환승 C-3-10), `country_index.json` (국가·별칭).
  - `c3_fallback.json`의 `transitRule.visaRequiredNationalitiesKo`는 순수환승(C-3-10) **사증
    대상국**(현재 시리아·수단·예멘·이집트 일반여권) 목록이다. 빌드 시 ISO로 해석되어
    `rules.json`의 `rules.c3Fallback.transitRule.visaRequiredIso2`로 들어가고, 체커가 "공항
    환승만" 답변에 사용한다. 매뉴얼(순수환승 발급대상)이 바뀌면 이 목록만 수정 후 재생성한다.
- `data/short-stay/rules.json`, `data/short-stay/sources.json` — **생성물**. 직접 편집하지 말 것.
- 출처 메타데이터(제목·기준일·신뢰도·충돌)는 `sources.json` + 각 fixture의 `notes`/`conflicts`.

## 갱신 절차
1. 변경된 공식 출처(법령/매뉴얼/고시/K-ETA 공지)를 확인하고 해당 **fixture**만 수정한다.
   - 충돌이 있으면 `conflicts`/`notes`에 `manualValue`·`storedValue`·`adopted`·`needsOfficialCheck`로 기록(삭제하지 말 것).
   - 외부 교차검증을 했다면 `sources.json` 생성 입력인 `update_short_stay_rules.mjs`의 해당
     source에 `crossCheckedAt`/`crossCheckUrls`를 남긴다(예: K-ETA 2026-12-31 연장).
2. 생성물 재생성:
   ```
   node scripts/update_short_stay_rules.mjs --from-fixtures
   ```
3. 검증:
   ```
   node scripts/check_short_stay_rules.mjs        # 엔진/판정 회귀 (66 checks)
   node scripts/check_short_stay_freshness.mjs     # 날짜 기반 신선도(0=fresh,1=stale)
   ```
4. UI 확인(선택): 메인페이지 "국적별 단기입국 경로 확인" → 대표 국가(일본·베트남·아르헨티나)
   결과의 결론·"반드시 확인할 점"·"자료 유의"·출처 표시 확인.
5. 커밋: fixture + 재생성된 rules/sources + (필요 시) 감사노트.

## 자동 모니터
- 예약 워크플로 `.github/workflows/short-stay-freshness.yml` (월 1회 + 수동 실행)가
  `check_short_stay_freshness.mjs`를 돌려, 출처가 임계값(기본 365일) 초과거나 K-ETA 면제
  종료일이 임박/경과하면 **`short-stay-freshness` 라벨의 GitHub 이슈를 자동 생성/갱신**한다.
- 임계값은 환경변수로 조정: `SHORT_STAY_STALE_DAYS`, `SHORT_STAY_EXPIRY_WARN_DAYS`.
- 이슈가 열리면 위 갱신 절차를 수행하고, 해결되면 다음 실행에서 이슈를 자동으로 닫는다.

## 알려진 재확인 항목(상시)
- 제주 B-2-2 고시(법무부고시 제2022-189호, 사본 2023-09-18) — 2022 고시라 항상 신선도 경고 대상.
  최신 고시 원문으로 재확인 필요.
- K-ETA 한시 면제: 현재 2026-12-31까지(외부 교차검증). 종료일 이후 연장·종료 재확인.
- 아르헨티나 B-2-1 체류기간(30일 vs 90일, 90일 채택), 이란 제주 입국불허(사본 22 vs 23개국,
  안전 우선 유지) — 공식 재확인 필요로 표기 중.
- 순수환승(C-3-10) 사증 대상국(시리아·수단·예멘·이집트 일반여권, 외교·관용여권 면제) —
  2026.5 사증발급 안내매뉴얼 기준. 매뉴얼 개정 시 대상국·여권범위 재확인 필요.
