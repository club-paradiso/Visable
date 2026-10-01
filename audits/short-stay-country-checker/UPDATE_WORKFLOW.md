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
  - 2026-10-01: 재외공관 게시물 「제주특별자치도 무사증 입국불허국가 변경(2025년 1월 업데이트)」의 **존재만** 확인
    (`jeju_b22_notice.json` → `laterNoticeObserved`, `bodyVerified: false`). 작업 환경에서 정부 도메인 접근이
    차단돼 본문 목록을 대조하지 못했으므로 국가 목록은 바꾸지 않았다. 대신 두 제주 출처의 confidence를 `low`로
    낮추고, 제주 판정마다 "이후 변경 고시가 게시됐으나 미반영" 경고를 띄운다. 본문을 대조해 목록을 갱신하면
    `laterNoticeObserved`를 제거하고 `noticeNo`·`effectiveDate`·`copyDate`·출처 id를 새 고시 기준으로 바꾼다.
  - 2026-10-01 교차확인(`laterNoticeObserved.corroboration`): 검색엔진 발췌로 주싱가포르 대사관 공지(2026-01-02 게시)와
    주불가리아 대사관 공지(2025-01)의 **입국불허 23개국 = 본 fixture 22개국 + 이란**을 확인. 이란 충돌 사유를 이 근거로 갱신했고
    국가 추가·삭제는 없음. 체류지역 확대허가 목록(34/1/29)은 2023-09-18 고시 총 64개국과 수는 같지만 이후 공지 본문을
    대조하지 못해 미확인으로 남김. 신선도 경고(STALE)는 유지.
- K-ETA 한시 면제: 현재 2026-12-31까지(외부 교차검증). 종료일 이후 연장·종료 재확인.
- 아르헨티나 B-2-1 체류기간(30일 vs 90일, 90일 채택), 이란 제주 입국불허(사본 22 vs 23개국,
  안전 우선 유지) — 공식 재확인 필요로 표기 중.
- 순수환승(C-3-10) 사증 대상국(시리아·수단·예멘·이집트 일반여권, 외교·관용여권 면제) —
  2026.5 사증발급 안내매뉴얼 기준. 매뉴얼 개정 시 대상국·여권범위 재확인 필요.
