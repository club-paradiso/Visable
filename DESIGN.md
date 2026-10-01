---
version: "2026.10"
name: Visable
description: >
  대한민국 비자·체류 정보 안내 플랫폼(Visable). 공식 출처 기반 civic-tech.
  신뢰감 있고 차분하며 공적 질감을 유지하는 따뜻한 종이+잉크 시각 언어.
  색 토큰의 단일 진실 출처는 index.html의 civic token layer
  (":root:not([data-theme=\"archive_diary\"])", UX-10 Foundations)이며,
  scripts/check_civic_tokens.mjs가 그 값으로 WCAG 대비 하한을 계산한다.
  아래 colors 값은 그 층을 옮겨 적은 것이다. 값이 다르면 index.html이 맞다.

colors:
  # 브랜드 (civic layer CSS 변수 → 이 문서 키)
  primary:        "#177366"   # --ac
  primary-deep:   "#0B4F44"   # --cta / --ac2 (기본 CTA, AAA 7:1 하한)
  primary-hover:  "#0B4F44"   # --ac2
  primary-mint:   "#3BE4B8"   # 다크 테마 --ac
  accent:         "#D95C47"   # --cy
  accent-deep:    "#D95C47"   # --cy (별도 deep 토큰 없음)
  amber:          "#F2C879"   # --cWk (경고는 color-mix(--cWk 38%, --t1))
  # 중립 — 따뜻한 종이+잉크
  neutral:        "#F7F4EF"   # --bg0
  surface:        "#FFFCF5"   # --bg1
  surface-2:      "#F7F4EF"   # --bg0
  text:           "#1C1F29"   # --t1 (본문 AA 4.5:1 하한)
  text-muted:     "#4D5261"   # --t2
  border:         "#E6E6EE"   # --bd
  # 다크모드 서피스 ([data-theme="dark"] + body[data-theme="dark"] 재정의)
  dark-bg:        "#062A22"   # --bg0
  dark-surface:   "#0D3129"   # --bg1 (body[data-theme="dark"])
  dark-text:      "#F4EFE4"   # --t1
  dark-primary:   "#3BE4B8"   # --ac

typography:
  hero-display:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 4.5rem
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: -0.02em
  h1:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 2.5rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.015em
  h2:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: -0.01em
  h3:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.4
  body-lg:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 1.0625rem
    fontWeight: 400
    lineHeight: 1.75
  body-md:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.65
  body-sm:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.6
  label-caps:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 0.75rem
    fontWeight: 600
    letterSpacing: 0.08em
  label-md:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 0.875rem
    fontWeight: 500
  stat-number:
    fontFamily: "Pretendard Variable, Pretendard"
    fontSize: 3rem
    fontWeight: 800
    letterSpacing: -0.04em

rounded:
  xs:   4px
  sm:   8px
  md:   12px
  lg:   16px
  xl:   20px
  2xl:  24px
  pill: 999px

spacing:
  1:   4px
  2:   8px
  3:   12px
  4:   16px
  5:   24px
  6:   32px
  7:   48px
  8:   64px
  9:   96px
  10:  128px

components:
  # ─ 버튼
  button-primary:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.md}"
    padding: "0 24px"
    height: 52px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0 20px"
    height: 44px
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: 40px
  # ─ 칩 / 배지
  chip:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    height: 32px
    padding: "0 14px"
  chip-active:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.pill}"
    height: 32px
    padding: "0 14px"
  visa-code-badge:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.primary-deep}"
    rounded: "{rounded.sm}"
    padding: "3px 10px"
  # ─ 카드
  visa-result-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    padding: "20px"
  modal-box:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: 18px
    padding: "24px"
  search-bar:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-text}"
    rounded: "{rounded.lg}"
    padding: "0 20px"
    height: 52px
  ai-answer-card:
    backgroundColor: "{colors.dark-bg}"
    textColor: "{colors.dark-text}"
    rounded: "{rounded.lg}"
    padding: "24px 28px"
  ai-kicker:
    backgroundColor: "transparent"
    textColor: "{colors.primary-mint}"
    rounded: "{rounded.xs}"
    padding: "0"
  section-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.xl}"
    padding: "32px"
  chip-dark-active:
    backgroundColor: "{colors.dark-primary}"
    textColor: "{colors.dark-bg}"
    rounded: "{rounded.pill}"
    height: 32px
    padding: "0 14px"
  hikorea-banner:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.lg}"
    padding: "18px 24px"
  # ─ 입력
  input-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    height: 44px
    padding: "0 16px"
  input-placeholder:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.md}"
    height: 44px
    padding: "0 16px"
  # ─ 알림
  divider:
    backgroundColor: "{colors.border}"
    textColor: "{colors.text}"
    rounded: "{rounded.xs}"
    height: 1px
  warning-box:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.amber}"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  accent-label:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    rounded: "{rounded.xs}"
    padding: "2px 8px"
  error-label:
    backgroundColor: "transparent"
    textColor: "{colors.accent-deep}"
    rounded: "{rounded.xs}"
    padding: "2px 8px"
---

## Overview

Visable의 시각 언어는 세 단어로 요약된다: **신뢰(Trust) · 온기(Warmth) · 명확성(Clarity)**.

대한민국에서 체류 문제를 겪는 외국인 — 디지털 리터러시가 낮고 스트레스를 받는 사람이 주 사용자다. 이 플랫폼은 차갑고 관료적인 정부 UI가 아니라, 따뜻하되 공적 신뢰감이 있는 경험을 제공한다.

**디자인 레퍼런스:** Jackie Zhang(`jackiezhang.co.za`)의 스타일을 직역하지 않고 컨셉으로 번역. "느껴지되 보이지 않는 질감", "자발적이고 따뜻한 느낌", "경직된 디지털 그리드에서 유기적 리듬으로"의 세 원칙을 공공서비스 비자 플랫폼 맥락에 적용한 결과다.

**랜딩 서사 골격** (Figma Make `N695iXnoavEOSHITttdCCu` 컴포넌트 아키텍처 기반):
HeroGateway(기능적 진입 관문) → StatBridge(신뢰 수치) → FeatureTrust(기능을 신뢰 프레임으로) → AnagramBrandStory(브랜드 서사) → StartSection → RoadmapSection → FooterCTA.

## Colors

팔레트는 **Civic Teal(`--ac #177366`)을 단일 브랜드 강조**로, CTA는 더 진한 `--cta #0B4F44`로 쓰고, 나머지는 따뜻한 종이+잉크 중성 톤이다. 값의 출처는 index.html civic token layer(UX-10 Foundations)이며, `scripts/check_civic_tokens.mjs`가 배포 CSS에서 직접 대비를 계산해 하한(본문 AA 4.5:1, 기본 CTA AAA 7:1)을 강제한다.

전체 팔레트 (대비는 WCAG 2 공식으로 계산한 값):
- **CTA (`--cta #0B4F44`):** 기본 버튼 배경. `--bg1 #FFFCF5` 대비 9.25:1(AAA).
- **Primary (`--ac #177366`):** 링크, 배지, 체크마크, 성공 상태, 포커스. `--bg1` 대비 5.57:1, `--bg0` 대비 5.2:1(AA).
- **Accent (`--cy #D95C47`, Coral):** 강조 타이포·아이콘. `--bg1` 대비 3.68:1이므로 본문 크기 텍스트 단독 사용 금지(큰 글자·비텍스트 요소만).
- **Warning (`--cWk #F2C879`):** 직접 텍스트로 쓰지 않고 `color-mix(--cWk 38%, --t1)`로 만든 `--color-warning`을 쓴다.
- **Paper (`--bg0 #F7F4EF`, `--bg1 #FFFCF5`):** 페이지·카드 배경. 본문 `--t1 #1C1F29`는 `--bg0` 대비 14.98:1, 보조 `--t2 #4D5261`은 7.1:1.
- **Dark mode:** `[data-theme="dark"]`. `--bg0 #062A22`, `--t1 #F4EFE4`(13.45:1), `--ac #3BE4B8`(9.53:1).
- **archive_diary 테마:** civic layer에서 의도적으로 제외(`:root:not([data-theme="archive_diary"])`).

알려진 부채: index.html에는 이전 팔레트(초기 Emerald·Cyber Blue 포스터 테마) 변수 정의가 먼저 선언되고 civic layer가 뒤에서 덮어쓰는 구조가 남아 있다. 시각 회귀 테스트 없이 앞선 정의를 지우면 덮어쓰지 않은 변수가 바뀌므로, 정리는 화면 캡처 비교와 함께 별도로 한다.

## Typography

**Pretendard Variable 단독.** 한국어 가독성 최우선. `font-feature-settings: "ss01"` 권장.

**현재 코드의 문제:** 거의 모든 텍스트에 `font-weight: 900`이 적용돼 시각 피라미드가 사라졌다. 이것이 "구리다"는 피드백의 1번 원인이다. 무게 체계:

| 역할 | weight | 적용 대상 |
|---|---|---|
| Hero Display | 800 | 히어로 h1, DIASPORA→PARADISO 애너그램에만 |
| Heading | 700 | 섹션 타이틀(h2, h3) |
| Strong | 600 | 서브섹션 헤드, 버튼, 업라이트 레이블 |
| Body | 400 | 모든 설명 본문 |
| Meta | 400 + tracking | 영문 서브텍스트, 날짜, 코드 |

`stat-number`(카테고리 통계)는 800 유지 — 크기 대비가 있어 800이어도 과하지 않다. `stat-label`은 반드시 500 이하.

한국어 본문 필수: `word-break: keep-all; line-height: 1.65` 이상.

실제 `font-size`는 `clamp(min, vw, max)` 반응형으로 적용:
- hero-display: `clamp(2.5rem, 6vw, 4.5rem)`
- h1: `clamp(2rem, 4vw, 2.5rem)`
- h2: `clamp(1.75rem, 3vw, 2rem)`

## Layout

8pt 그리드. 컨테이너 3종:

| 이름 | 너비 | 사용처 |
|---|---|---|
| narrow | 720px | 히어로 카피, 브랜드 서사, 아나그램 |
| default | 960px | 대부분 섹션 |
| wide | 1180px | 검색 결과, 행정사·의료기관 리스트 |

거터: `clamp(1rem, 4vw, 2rem)`.

**섹션 리듬:** 동일한 `6rem·8rem` 반복이 단조로움의 원인. 의도적 밀도 차이:
- 히어로: `padding: clamp(5rem,12vh,9rem) 0 clamp(4rem,8vh,7rem)`
- 정보 밀도 높은 섹션(agentFinder, medFinder): `padding: 4rem 0`
- 브랜드 서사: `padding: 8rem 0` — 여백 자체가 메시지

반응형: 480(mobile-sm) / 768(tablet) / 1024(desk). 터치 타겟 최소 44px.

## Elevation & Depth

3계층 그림자:

| 레이어 | 값 | 용도 |
|---|---|---|
| Tier 1 | `0 1px 0 rgba(14,31,26,.04), 0 1px 2px rgba(14,31,26,.05)` | 헤어라인, 인라인 구분 |
| Tier 2 | `0 4px 12px rgba(14,31,26,.06), 0 1px 2px rgba(14,31,26,.04)` | 카드 기본 |
| Tier 3 | `0 12px 32px rgba(14,31,26,.10), 0 2px 6px rgba(14,31,26,.05)` | 모달, 드롭다운 |
| CTA Glow | `0 4px 18px rgba(14,163,123,.32), 0 2px 4px rgba(14,163,123,.18)` | Primary 버튼 hover |
| Glass | `0 16px 48px -8px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.10)` | 히어로 글래스 요소 |

**글래스모피즘:** `backdrop-filter: blur(20px)`, 배경 `rgba(255,255,255,0.13)`, 테두리 `rgba(255,255,255,0.20)`. **히어로 검색바에만** 적용 — 남용 금지.

## Shapes

**현재 문제:** 전 사이트에 `border-radius: 2rem(32px)` 반복. 이것이 "구리다"는 피드백의 2번 원인.

| 반경 | 값 | 용도 |
|---|---|---|
| xs | 4px | 배지, 코드 칩, 소형 태그 |
| sm | 8px | 인라인 버튼, 소형 카드 서브 요소 |
| md | 12px | 버튼(기본), 검색 입력, 소형 카드 |
| lg | 16px | 비자 결과 카드, 구비서류 카드, AI 답변 카드 |
| xl | 20px | 섹션 내 대형 그룹 카드 |
| 2xl | 24px | brandHero 통계 박스 |
| pill | 999px | 칩, 배지, 언어 토글, 키워드 칩 |
| modal | 18px | 모달 박스 고정값 |

**규칙:** 크기가 클수록 반경은 더 작게. 작은 요소일수록 더 둥글게.

## Components

모든 인터랙티브 컴포넌트: 44px 최소 터치 타겟, `:focus-visible` 시 `--ac` 기반의 3px 포커스 링.

**버튼 계층(한 화면에 동시 배치 규칙):**
- Primary 버튼은 화면당 1개. 부득이 2개면 나머지는 Secondary.
- Primary 컬러: `--cta(#0B4F44)` 배경 + `--bg1(#FFFCF5)` 텍스트 (9.25:1, WCAG AAA).

**Visa Result Card 정보 스캔 순서:**
① 코드 배지 + 한/영 명칭 → ② 매뉴얼 도메인 배지 → ③ 절차 컨트롤(세그먼티드) → ④ 해당 절차 문서만 → ⑤ 출처 블록.
문서 전체를 한 화면에 쏟지 않는다. 절차 탭으로 분리.

**HiKorea Banner:** 검색 결과 상단에 항상 노출. `primary-deep` 배경 + `neutral` 텍스트.

**Modal:** 최대 너비 540px(기본), 820px(직종코드). 진입 애니메이션: `scale(0.97)→scale(1)`, `200ms ease-out`.

## Do's and Don'ts

### Do
- Emerald를 단일 강조 컬러로 유지. 한 화면에 3개 이하.
- 한국어 본문에 `word-break: keep-all; line-height: 1.65` 이상.
- 비자 코드(`D-2`, `E-7`)는 항상 Badge 처리 — 본문 인라인 삽입 금지.
- 법적 면책 문구는 항상 화면 하단 뮤트 텍스트로.
- 섹션 간격에 의도적 밀도 차이.
- 터치 타겟 44px 최소.
- `[data-theme="dark"]` 어트리뷰트 방식 유지.

### Don't
- **제품명은 "Visable".** 하위 화면은 "Waymaker"·"New Home"처럼 이름만 쓴다("… by Paradiso" 표기 금지). "Club Paradiso"는 팀·저작권 표기로만 쓴다.
- 공식 법적 판정·자격 보증·HiKorea 대체 암시 금지.
- `font-weight: 900`을 h2 이하 사용 금지 — 위계 붕괴.
- 전 섹션에 동일한 `border-radius: 2rem` 적용 금지.
- 글래스모피즘 히어로 외 남용 금지.
- Coral(`--cy #D95C47`)을 본문 크기 텍스트·경계선·배경에 사용 금지(대비 3.68:1).
- 새 코드에 `!important` 추가 금지(기존 사용분은 cascade 부채로, 시각 회귀 확인과 함께 줄인다).
