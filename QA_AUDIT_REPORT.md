# Paradiso — Pre-Launch QA Audit Report
**감사 일자**: 2026-06-13  
**대상**: https://lucanomics.github.io/Paradiso/ (로컬 정적 서버 http://127.0.0.1:8099 병행)  
**감사 범위**: 39 체류자격 A-1 ~ G-1 전수 (Waymaker 제외)  
**감사 방법**: 정적 코드 분석 (index.html 20,677줄, visa_data.json, i18n JSON) + Playwright 헤드리스 Chromium 실황 재검증  
**검증 도구**: Playwright 1.56.1 + pre-installed Chromium `/opt/pw-browsers/chromium-1194/`  

---

## 목차
1. [요약 (Executive Summary)](#1-요약)
2. [P1 — 이민 행정관 시각](#2-p1--이민-행정관)
3. [P2 — 재외 한국인 시각](#3-p2--재외-한국인)
4. [P3 — 유학생·다언어 사용자 시각](#4-p3--유학생다언어)
5. [P4 — UX/UI 디자이너 시각](#5-p4--uxui-디자이너)
6. [P5 — 개발자 시각](#6-p5--개발자)
7. [P6 — E-9 비전문 이주노동자 시각](#7-p6--e-9-이주노동자)
8. [통합 우선순위 테이블](#8-통합-우선순위)
9. [검증 상태 요약](#9-검증-상태)

---

## 1. 요약

| 구분 | 건수 |
|------|------|
| **P0 차단급** (런칭 전 필수 수정) | 3 |
| **P1 고위험** (런칭 전 강력 권고) | 7 |
| **P2 중위험** (런칭 후 단기 개선) | 11 |
| **통과 (PASS)** | 12 |
| **여전히 검증불가** | 4 |

### P0 요약
1. **zh-CN 204개 미번역** — 중국어 모드에서 한국어 그대로 노출 (1,101 Hangul 런 실측)
2. **통계 수치 불일치** — "39가지" 산문 5곳 vs 실측 표시값 42
3. **동의 없는 IP 지오로케이션** — archive_diary 테마 로드 시 외부 4개 API 자동 호출

---

## 2. P1 — 이민 행정관

> **시각**: 법적 정확성, 공식 정보 일관성, 규정 준수

| # | 항목 | 상태 | 등급 | 증거 | 개선안 |
|---|------|------|------|------|--------|
| 1.1 | "39가지 체류자격" 산문 vs 실측 42 표시 | **FAIL** | P0 | 코드 12396, 12802, 12824, 12844, 12871줄 하드코딩 "39가지"; 실황 stat 카드: work 18 / study 6 / residence 6 / visit 12 = 42 | 산문을 동적 `coverageBucket()` 반환값으로 교체하거나, 파일럿(K-STAR, REGION-S, YOUTH-STAY) + D-4-1/D-4-2K를 명시적으로 제외하는 필터 추가 |
| 1.2 | 코드 주석 허위 — "파일럿 제외로 39 유지" | **FAIL** | P1 | index.html 18671-18673: `// pilot programs intentionally excluded`; 그러나 coverageBucket()은 파일럿도 stat 버킷에 포함시킴 | 주석 수정 또는 실제 코드와 일치하도록 필터 구현 |
| 1.3 | `visa_data.json` 전 42건 `verified:false` | **FAIL** | P1 | 모든 레코드 `sourceManualStatus.verified:false`, `needsManualReview:true` | 공식 출입국·외국인청 매뉴얼 대조 후 수동 검증 완료 표시 필요 |
| 1.4 | 근거 출처 카드 — 주소·전화번호 검증 불가 | 검증불가 | — | 출입국·외국인청, HiKorea 공식 URL 표기는 정적 텍스트; 실황 클릭 불가 환경 | 외부 링크 정기 점검 체계 도입 권고 |
| 1.5 | 법령 내용 vs 실제 매뉴얼 정확도 | 검증불가 | — | OCR txt 파일은 감사 보조자료; 법적 요건 직접 대조 미수행 | 이민법 전문가 법적 감수 필수 |
| 1.6 | 절차 구분 혼재 위험 (사증발급 vs 체류) | 주의 | P1 | CLAUDE.md 규칙 명시; 코드상 렌더러 분리 여부 전수 확인 미완 | 각 체류자격별 절차 탭 레이블 전수 확인 |
| 1.7 | `TODO` 배포 주석 노출 | **FAIL** | P2 | index.html 17175: `// 기관별 방문예약 딥링크 미확보 — 관할기관별 동적 연결은 후속 작업` | 배포 전 TODO 주석 제거 또는 이슈 트래커로 이관 |

---

## 3. P2 — 재외 한국인

> **시각**: 영어 사용 불편, 정보 접근성, 복잡한 자격 탐색

| # | 항목 | 상태 | 등급 | 증거 | 개선안 |
|---|------|------|------|------|--------|
| 2.1 | EN 모드 빈 결과 초기화 버튼 — 한국어 하드코딩 | **FAIL** | P1 | Playwright 실측: `#resetFilters` 버튼 텍스트 "필터 초기화" — EN 모드에서도 동일 | i18n 키 적용 (`tx('resetFilters')` 등) |
| 2.2 | 3개 i18n 키 누락 (`medTotalCount`, `agentRegionAll`, `agentTotalCount`) | **FAIL** | P1 | 런타임 콘솔 `[i18n] missing key:` 경고 실측 확인 | 3개 키를 ko/en/zh-CN 모두에 추가 |
| 2.3 | EN 메인 퍼널 — 실황 확인 | **PASS** | — | Hero, 면책고지, pathway, footer, 매뉴얼 카드 모두 영어 렌더링 확인 | — |
| 2.4 | 검색 결과 내 영어 체류자격 이름 표시 | **PASS** | — | `data/i18n/visa-names.json` EN 키 존재; 실황 검색 정상 | — |
| 2.5 | F-4 경로 가이드 | **PASS** | — | `#f4RouteGuide` 가시성 확인, 6개 버튼 렌더링 | — |
| 2.6 | D-4-2K / K-STAR / REGION-S / YOUTH-STAY `visa-names.json` zh-CN: null | 주의 | P2 | 파일 직접 확인; EN은 정상 | zh-CN 이름 추가 |

---

## 4. P3 — 유학생·다언어 사용자

> **시각**: 중국어·영어 UI 품질, 다국어 일관성

| # | 항목 | 상태 | 등급 | 증거 | 개선안 |
|---|------|------|------|------|--------|
| 3.1 | zh-CN 204개 값 한국어 그대로 | **FAIL** | **P0** | `data/i18n/zh-CN.json` 정적 분석; Playwright DOM 실측 1,101 Hangul 런 | 204개 키 중국어 번역 완료 (상세 목록 §9 참조) |
| 3.2 | zh-CN 해당 UI 블록 | **FAIL** | P0 | `brandHeroTitle` 중국어 OK; `featureBody`, `pathwayCopy`, `featureChecks`, `sourceCards`, `toolCards`, `howSteps`, `reminder*`, `footer*`, `about*`, `roadmap*`, `agent*`, `med*`, `jobCode*` (8), `lawSource*` (6), `sourceChip*`, `subcodeGroup*`, `docDefinitionNeeded`, `resultEmptyBody` 한국어 | 위 목록 전체 번역 |
| 3.3 | 25곳 `currentLanguage==='en'?…:한국어` — zh 한국어 낙하 | **FAIL** | P1 | index.html 13649, 13666, 13694, 14784, 14796 등 25개소 | 삼항 연산자를 `tx()` 호출로 교체 |
| 3.4 | `official-terms.json` 21개 중 대부분 `zh-CN:null` | **FAIL** | P2 | 파일 직접 확인; `annotateOfficialDocLabel()` 에서 zh 어노테이션 없음 | zh-CN 번역 추가 |
| 3.5 | `doc_master.json` 101개 항목 `zh_name` 필드 없음 | **FAIL** | P2 | 파일 직접 확인 | `zh_name` 추가 또는 `DOC_DICT`에 zh 매핑 병행 |
| 3.6 | `LANGUAGE_SUPPORT` 'full' 허위 표기 | **FAIL** | P1 | index.html 18021: `ko:'full', en:'full', 'zh-CN':'full'`; zh-CN 실제는 대규모 미번역 | `'zh-CN':'partial'`로 수정 및 언어 선택 UI에 "번역 진행 중" 배지 표시 |
| 3.7 | 베트남어·네팔어·크메르어 미지원 | 주의 | P2 | `LANGUAGE_OPTIONS` ko/en/zh-CN만 존재 (index.html 18010-18014) | 로드맵 명시 또는 향후 지원 언어 공지 |
| 3.8 | EN 807개 Hangul 런 — 비자/서류 고유명사 | **PASS** | — | 분석 결과 정책상 정상 (한국어 고유명사 병기) | 의도적이라면 고유명사 표기 일관성 가이드라인 문서화 |

---

## 5. P4 — UX/UI 디자이너

> **시각**: 시각 일관성, 접근성, 반응형, 브랜드 무결성

| # | 항목 | 상태 | 등급 | 증거 | 개선안 |
|---|------|------|------|------|--------|
| 4.1 | Footer 소자 대비율 4.19:1 @ ~11.8px | **FAIL** | P1 | Playwright 실측; WCAG AA 기준 소자 4.5:1 (12px↓) 미달 | 글자 크기 14px↑ 또는 색상 밝기 조정 |
| 4.2 | 헤더 컨트롤 40px (도시·테마·언어) — 44px 자체 기준 미달 | **FAIL** | P1 | index.html 150-151: `--btn-h-sm:32px`, `--btn-h-md:40px`; Playwright 실측 390px 뷰포트 | 최소 44×44px로 확대 |
| 4.3 | `<meta theme-color="#0f172a">` — 실제 크림 배경과 불일치 | **FAIL** | P2 | index.html 27줄; civic_editorial 기본 배경 크림색 | 테마별 동적 theme-color 또는 배경 일치 색상 |
| 4.4 | `!important` 1,049개 | 주의 | P2 | Grep 전수 계산; DESIGN.md "no !important" 명시와 상충 | 계단식 우선순위 재설계; 최소 필수만 유지 |
| 4.5 | `--color-accent`/`--ac` 이중 accent 토큰 | 주의 | P2 | index.html 104-162줄 CSS tokens | 단일 토큰으로 통합; DESIGN.md 갱신 |
| 4.6 | archive_diary 테마 — 동의 없는 IP 지오로케이션 4건 | **FAIL** | **P0** | index.html 19076-19107: `ipapi.co` → `ip-api.com` → `restcountries.com` + `flagcdn.com`; Playwright 네트워크 로그 확인 | GDPR/개인정보보호법 준수를 위한 명시적 동의 획득 또는 기능 제거 |
| 4.7 | HiKorea 가이드 스크린샷 5단계 플레이스홀더 | **FAIL** | P2 | index.html 17167, 17174-17179: `hkScreenshotPending` 박스 5개 | 실제 스크린샷 삽입 또는 플레이스홀더 제거 후 텍스트로 대체 |
| 4.8 | Figma Make URL + "후보" 코드명 + 디자이너 실명 노출 | **FAIL** | P1 | index.html 37, 2575줄 | 배포 전 제거 |
| 4.9 | DESIGN.md 내용 vs 실제 구현 다수 불일치 | 주의 | P2 | DESIGN.md "Pretendard only, no fw:900 below h2" vs 실제 Unbounded/Pixelify Sans 사용; !important 등 | DESIGN.md 현행화 |

---

## 6. P5 — 개발자

> **시각**: 코드 품질, 런타임 오류, 데이터 무결성, 보안

| # | 항목 | 상태 | 등급 | 증거 | 개선안 |
|---|------|------|------|------|--------|
| 5.1 | `DOC_DICT` 한국어 전용 101개 — zh 낙하 | **FAIL** | P1 | index.html 13150-13174; `doc_master.json` `zh_name` 없음 | DOC_DICT에 en/zh 병렬 맵 추가 |
| 5.2 | 미사용 ID fallback `서류명 확인 필요: doc_xxx` 노출 위험 | 잠재 | P1 | index.html 16291, 17438; 현재 활성 0건이나 향후 데이터 오류 시 노출 | safe fallback을 `tx('docDefinitionNeeded')`로 통일 |
| 5.3 | `BOOTSTRAP_KO_FALLBACK` 스텁에 TB-1/SCN-6 죽은 칩 | **FAIL** | P2 | index.html 18030-18055; JavaScript 비활성화 환경에서만 노출 | 폴백 스텁 갱신 또는 제거 |
| 5.4 | 페이지 로드 오류 0건, 로컬 404 0건 | **PASS** | — | Playwright 콘솔 감시 확인 | — |
| 5.5 | 검색 플로우 정상 | **PASS** | — | 실황 테스트 통과 | — |
| 5.6 | Railway 백엔드 (`web-production-14f9a.up.railway.app`) 실황 상태 | 검증불가 | — | 원격 API 직접 호출 불가 환경 | 배포 전 헬스체크 엔드포인트 확인 |
| 5.7 | `coverageBucket()` null 라우팅 — `faq/scn/nhis` 카테고리 | 주의 | P2 | index.html 18674-18688; null 버킷 → 통계에서 제외됨 | 의도적이면 주석 명시, 아니면 버킷 지정 |
| 5.8 | `short-stay-checker.js` / `f4-route-guide.js` defer 로드 | **PASS** | — | F-4 실황 동작 확인; short-stay는 별도 진입점 | — |
| 5.9 | `<html lang="ko">` 정적 선언 → `applyLanguage()` 동적 교체 | **PASS** | — | index.html 6줄 정적, `applyLanguage()` 18331↑에서 덮어씀; 정상 작동 | — |

---

## 7. P6 — E-9 이주노동자

> **시각**: 정보 명확성, 언어 장벽, 핵심 정보 도달 난이도

| # | 항목 | 상태 | 등급 | 증거 | 개선안 |
|---|------|------|------|------|--------|
| 6.1 | E-9 정보 한국어 전용 (zh-CN P0와 동일) | **FAIL** | P0 | zh-CN 미번역 범위 §3.1과 동일 | zh-CN 번역 완료 시 해소 |
| 6.2 | 베트남어·네팔어 미지원 | **FAIL** | P1 | E-9 주요 언어권; 현재 ko/en/zh-CN만 | 중장기 로드맵에 추가 또는 외부 링크 제공 |
| 6.3 | 비자 이름 영어/한국어 병기 — 고유명사 유지 | **PASS** | — | E-9 검색 시 영문병기 확인 | — |
| 6.4 | 모바일 44px 탭 기준 미달 (P4.2와 동일) | **FAIL** | P1 | 390px 뷰포트 실측 40px | §4.2와 동일 |
| 6.5 | 실제 기기 터치 에르고노믹스 | 검증불가 | — | 시뮬레이터 환경; 실기기 미테스트 | 실기기 QA 권고 |
| 6.6 | 면책고지·공식출처 경고문 보존 여부 | **PASS** | — | 실황 면책고지 DOM 확인 | — |

---

## 8. 통합 우선순위

### P0 — 런칭 차단 (즉시 수정)

| ID | 제목 | 영향 범위 |
|----|------|-----------|
| **P0-1** | zh-CN 204개 미번역 (Hangul 1,101 런) | 모든 중국어 사용자 |
| **P0-2** | "39가지" 산문 vs 실측 42 카운트 불일치 | 법적 신뢰성, 전체 방문자 |
| **P0-3** | 동의 없는 IP 지오로케이션 4개 API (archive_diary) | GDPR·개인정보보호법 위반 위험 |

### P1 — 런칭 전 강력 권고

| ID | 제목 | 근거 |
|----|------|------|
| **P1-1** | 25곳 zh 한국어 낙하 (`currentLanguage==='en'?…:KO`) | zh-CN P0 동반 수정 |
| **P1-2** | 3개 i18n 키 누락 (`medTotalCount`, `agentRegionAll`, `agentTotalCount`) | 콘솔 경고 런타임 확인 |
| **P1-3** | `LANGUAGE_SUPPORT` `'zh-CN':'full'` 허위 | 사용자 기대 오도 |
| **P1-4** | Footer 소자 대비율 4.19:1 (WCAG AA 미달) | 접근성 법적 위험 |
| **P1-5** | 헤더 컨트롤 40px — 44px 자체 기준 미달 | 모바일 UX |
| **P1-6** | EN 빈 결과 초기화 버튼 한국어 하드코딩 | 영어 사용자 혼란 |
| **P1-7** | Figma Make URL + "후보" 코드명 + 디자이너 실명 노출 | 개인정보·내부정보 노출 |
| **P1-8** | `visa_data.json` 전건 `verified:false` | 법적 정확성 보장 불가 |
| **P1-9** | `DOC_DICT` 한국어 전용 — 영어/중국어 사용자에게 doc 이름 한국어 노출 | P3 연계 |
| **P1-10** | E-9 주요 언어(베트남어·네팔어) 미지원 | 핵심 사용자 소외 |

### P2 — 런칭 후 단기 개선 (4주 이내)

| ID | 제목 |
|----|------|
| **P2-1** | `<meta theme-color>` 배경색과 불일치 |
| **P2-2** | `!important` 1,049개 — CSS 구조 개선 |
| **P2-3** | `--color-accent`/`--ac` 이중 토큰 통합 |
| **P2-4** | HiKorea 가이드 스크린샷 5단계 플레이스홀더 |
| **P2-5** | `official-terms.json` zh-CN 번역 추가 |
| **P2-6** | `doc_master.json` `zh_name` 필드 추가 |
| **P2-7** | `visa-names.json` 파일럿 코드 zh-CN:null |
| **P2-8** | `BOOTSTRAP_KO_FALLBACK` 죽은 칩 (TB-1/SCN-6) |
| **P2-9** | `coverageBucket()` null 라우팅 의도 명시 |
| **P2-10** | 코드 주석 허위 "파일럿 제외로 39 유지" |
| **P2-11** | DESIGN.md 현행화 |

---

## 9. 검증 상태 요약

### 실황 확인 완료 (Playwright 헤드리스 Chromium)

| 항목 | 결과 | 방법 |
|------|------|------|
| zh-CN Hangul 런 수 | **1,101건 확인** | DOM innerHTML Hangul regex 계수 |
| zh-CN brandHeroTitle | 중국어 OK | DOM 텍스트 추출 |
| zh-CN featureBody | **한국어 노출 확인** | DOM 텍스트 추출 |
| 통계 카드 수치 | **work 18 / study 6 / res 6 / visit 12 = 42** | IntersectionObserver 트리거 후 DOM 읽기 |
| EN 메인 퍼널 | **전체 영어** (PASS) | DOM 텍스트 + Hangul 검사 |
| IP 지오로케이션 요청 | **ipapi.co + ip-api.com + restcountries + flagcdn 확인** | Playwright 네트워크 인터셉트 |
| 콘솔 경고 | **`[i18n] missing key: medTotalCount` 외 2건** | 콘솔 리스너 |
| Footer 대비율 | **4.19:1 @ ~11.8px 실측** | `getComputedStyle` + 대비 공식 |
| 헤더 컨트롤 크기 | **40px @ 390px 뷰포트** | `getBoundingClientRect` |
| EN 초기화 버튼 | **"필터 초기화" 한국어 확인** | DOM 텍스트 |
| F-4 Route Guide | **#f4RouteGuide visible, 6버튼** (PASS) | DOM visibility + 자식 요소 수 |
| 페이지 오류 / 404 | **0건** (PASS) | 콘솔 error 리스너 |

### 여전히 검증불가

| 항목 | 이유 |
|------|------|
| 실제 폰트 글리프 렌더링 (Pretendard/Unbounded/Pixelify) | 헤드리스 환경 폰트 렌더링 신뢰 불가; 실기기 필요 |
| Railway 백엔드 라이브 상태 | 원격 API 호출 차단 환경 |
| 실기기 터치 에르고노믹스 | 시뮬레이터와 실기기 차이 |
| 법령 내용 vs 공식 매뉴얼 정확도 | 이민법 전문가 감수 필요 (기술 감사 범위 외) |

---

## 부록 A — zh-CN 미번역 키 목록 (204개 영향 네임스페이스)

```
brandHeroTitle (부분 — 메인 타이틀 OK, 서브 한국어)
featureBody.*
pathwayCopy.*
featureChecks.*
sourceCards.*
toolCards.*
howSteps.*
reminder*
footer*
about*
roadmap*
agent* (agentRegionAll, agentTotalCount 포함 — 키 자체 없음)
med* (medTotalCount 포함 — 키 자체 없음)
jobCode* (8개 키)
lawSource* (6개 키)
sourceChip*
subcodeGroup*
docDefinitionNeeded
resultEmptyBody
```

---

## 부록 B — 검증 스크립트 실행 환경

```
OS: Linux 6.18.5
Playwright: 1.56.1 (/opt/node22/lib/node_modules/playwright)
Chromium: /opt/pw-browsers/chromium-1194/chrome-linux/chrome
로컬 서버: python3 -m http.server 8099 --bind 127.0.0.1
환경변수: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
```

---

*이 보고서는 기술적 렌더링·데이터 무결성 감사 결과입니다. 법적 이민 요건의 정확성은 별도 법률 전문가 검토가 필요합니다.*
