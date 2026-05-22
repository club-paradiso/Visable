---
version: alpha
name: Paradiso
description: >
  대한민국 비자·체류 정보 안내 플랫폼. 제주 출입국 특화 civic-tech.
  신뢰감 있고 차분하며 공적 질감을 유지하는 따뜻한 종이+잉크 시각 언어.

colors:
  # 브랜드 (컴포넌트에서 직접 참조)
  primary:        "#0EA37B"
  primary-deep:   "#085E48"
  primary-hover:  "#0c8c69"
  primary-mint:   "#7DD8B8"
  accent:         "#FF6B5B"
  accent-deep:    "#E0513E"
  amber:          "#E68A3A"
  # 중립 — 따뜻한 종이+잉크
  neutral:        "#F4EEE0"
  surface:        "#FCFAF5"
  surface-2:      "#FBF5E6"
  text:           "#0E1F1A"
  text-muted:     "#7A8580"
  border:         "#C9BFA5"
  # 다크모드 서피스
  dark-bg:        "#0B2A24"
  dark-surface:   "#113B32"
  dark-text:      "#F3EEDF"
  dark-primary:   "#34D4A8"

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

Paradiso의 시각 언어는 세 단어로 요약된다: **신뢰(Trust) · 온기(Warmth) · 명확성(Clarity)**.

대한민국에서 체류 문제를 겪는 외국인 — 디지털 리터러시가 낮고 스트레스를 받는 사람이 주 사용자다. 이 플랫폼은 차갑고 관료적인 정부 UI가 아니라, 따뜻하되 공적 신뢰감이 있는 경험을 제공한다.

**디자인 레퍼런스:** Jackie Zhang(`jackiezhang.co.za`)의 스타일을 직역하지 않고 컨셉으로 번역. "느껴지되 보이지 않는 질감", "자발적이고 따뜻한 느낌", "경직된 디지털 그리드에서 유기적 리듬으로"의 세 원칙을 공공서비스 비자 플랫폼 맥락에 적용한 결과다.

**랜딩 서사 골격** (Figma Make `N695iXnoavEOSHITttdCCu` 컴포넌트 아키텍처 기반):
HeroGateway(기능적 진입 관문) → StatBridge(신뢰 수치) → FeatureTrust(기능을 신뢰 프레임으로) → AnagramBrandStory(브랜드 서사) → StartSection → RoadmapSection → FooterCTA.

## Colors

팔레트는 **Emerald(`#0EA37B`)를 단일 브랜드 강조**로 하고, 나머지는 따뜻한 종이+잉크 중성 톤으로 구성된다.

전체 팔레트:
- **Primary (`#0EA37B`, Emerald):** CTA 버튼 배경, 배지, 체크마크, 성공 상태. 화면당 3개 이하.
- **Primary Deep (`#085E48`):** 히어로 헤더 배경, 버튼 텍스트 대비 기반색(대비율 충족), 다크 서피스. WCAG AA 준수를 위해 버튼 primary-deep에서 neutral 텍스트 조합 사용.
- **Primary Mint (`#7DD8B8`):** Paradiso AI 테마, 어두운 배경에서의 민트 강조.
- **Accent (`#FF6B5B`, Coral):** 카테고리 통계 숫자, 강조 타이포. 경계선·배경 사용 금지.
- **Neutral (`#F4EEE0`, Paper):** 페이지 기본 배경. 순백 대신 따뜻한 오프화이트.
- **Dark mode:** `dark-bg(#0B2A24)` 기반, `dark-primary(#34D4A8)` 강조. `[data-theme="dark"]` 어트리뷰트로 토글.

⚠️ **WCAG 경고:** Emerald(`#0EA37B`) + 흰 텍스트 대비율 3.21:1 — AA 미달. 따라서 Primary 버튼은 `primary-deep(#085E48)` 배경 + `neutral(#F4EEE0)` 텍스트 조합을 사용한다(대비율 8.4:1, AAA 통과).

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

모든 인터랙티브 컴포넌트: 44px 최소 터치 타겟, `:focus-visible` 시 `0 0 0 3px rgba(14,163,123,0.35)` 포커스 링.

**버튼 계층(한 화면에 동시 배치 규칙):**
- Primary 버튼은 화면당 1개. 부득이 2개면 나머지는 Secondary.
- Primary 컬러: `primary-deep(#085E48)` 배경 + `neutral(#F4EEE0)` 텍스트 (WCAG AAA). Emerald 배경+흰 텍스트는 AA 미달.

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
- **"Paradiso 39" 표기 절대 금지.** 제품명은 "Paradiso"만.
- 공식 법적 판정·자격 보증·HiKorea 대체 암시 금지.
- `font-weight: 900`을 h2 이하 사용 금지 — 위계 붕괴.
- 전 섹션에 동일한 `border-radius: 2rem` 적용 금지.
- 글래스모피즘 히어로 외 남용 금지.
- Coral(`#FF6B5B`)을 경계선·배경 사용 금지.
- `!important` CSS 사용 금지.
- Emerald(`#0EA37B`) + 흰 텍스트 조합 금지 — WCAG AA 미달(3.21:1).
