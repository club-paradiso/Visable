---
version: rebrand-proposal-v1
status: proposal            # 승인 시 루트 DESIGN.md를 대체. 그 전까지 프로덕션 비반영.
house: Club Paradiso
description: >
  Paradiso를 제품명에서 모(母)브랜드로 끌어올리는 House-of-Brands 전환.
  Visable(이성·명료) = 비자·체류 정보 제품, Paradiso(감성·온기) = 하우스 서사.
  토스 디자인 시스템(TDS) 가이드를 레이아웃·UX 라이팅·다크패턴 기준으로 적극 참조하되,
  토스의 컬러·로고·그래픽 자산은 복제하지 않는다(파트너 구분 원칙).

# ── 브랜드 아키텍처 ─────────────────────────────────────────────
brand:
  model: house-of-brands     # 기존 branded-house("Paradiso X")에서 전환
  house:
    name: Club Paradiso
    role: 스튜디오 / 퍼블리셔. 디아스포라→낙원 origin story와 온기를 담는 자리.
    voice-bias: emotional
  products:
    visable:
      name: Visable
      lockup: "Visable by Paradiso"   # 전환기 기본 표기(엔도스드 브랜드)
      shorthand: "Visable"            # 앱바·파비콘 등 협소 UI 한정
      domain: 비자·체류 정보
      theme: visable
      file: index.html
      voice-bias: rational
      meaning: "Visa + -able(가능하게) + Visible(보이게) — 카테고리를 즉시 말하는 이성 네임"
    new-home:
      name: New Home
      lockup: "New Home by Paradiso"   # 구 "Paradiso: New Home"
      domain: 국적·귀화 안내
      theme: paradiso-warm
      file: new-home.html
      voice-bias: emotional
    waymaker:
      name: Waymaker
      lockup: "Waymaker by Paradiso"    # 하우스 레벨 엔도스(두 제품에서 모두 호출되므로)
      domain: AI 안내 도우미
      theme: visable-dark
      file: ai.html
      note: "Visable·New Home 양쪽에서 진입하므로 제품(Visable)이 아닌 하우스(Paradiso)로 엔도스. 단독 결정 필요 시 재논의."

# ── 코어 토큰(하우스 공유 DNA — 제품 불문 동일) ──────────────────
colors:
  # 브랜드 강조 — Emerald 단일. ※ 토스 블루(#3182F6) 절대 차용 금지.
  primary:        "#0EA37B"
  primary-deep:   "#085E48"
  primary-hover:  "#0c8c69"
  primary-mint:   "#7DD8B8"
  accent:         "#FF6B5B"
  accent-deep:    "#E0513E"
  amber:          "#E68A3A"
  # 중립 — 따뜻한 종이+잉크
  neutral:        "#F4EEE0"   # warm paper (Paradiso-warm base)
  surface:        "#FCFAF5"   # near-white clean (Visable base)
  surface-2:      "#FBF5E6"
  text:           "#0E1F1A"
  text-muted:     "#7A8580"
  border:         "#C9BFA5"
  # 다크 서피스
  dark-bg:        "#0B2A24"
  dark-surface:   "#113B32"
  dark-text:      "#F3EEDF"
  dark-primary:   "#34D4A8"

# ── 제품별 테마(같은 팔레트, 다른 온도·밀도·장식) ────────────────
themes:
  # Visable = clarity-forward. 깨끗한 베이스, 높은 위계 대비, 장식 최소.
  visable:
    base-surface:   "{colors.surface}"     # near-white, 더 깔끔
    decoration:     minimal                # 브러시 워드마크·아나그램·kitsch 레이어 미사용
    density:        comfortable-clear       # 토스식 정보 위계·여백 규율
    accent-usage:   confident-sparse        # 핵심 액션에만 Emerald, 화면당 ≤3
    wordmark:       "Visable (set type, 800/-0.02em) + 'by Paradiso' endorser line"
  # Paradiso-warm = editorial. 종이 질감, 브러시, 서정.
  paradiso-warm:
    base-surface:   "{colors.neutral}"     # warm paper, 더 따뜻
    decoration:     editorial              # 브러시 워드마크 허용, 아나그램 = 하우스 서사
    density:        lyrical                # 여백 자체가 메시지
    accent-usage:   warm-sparse
  visable-dark:
    base-surface:   "{colors.dark-bg}"
    decoration:     minimal
    accent-usage:   mint-on-dark           # primary-mint / dark-primary

typography:
  fontFamily: "Pretendard Variable, Pretendard"   # 단일. 신규 웹폰트 추가 금지.
  hero-display:  { fontSize: clamp(2.5rem,6vw,4.5rem), fontWeight: 800, lineHeight: 1.15, letterSpacing: -0.02em }
  h1:            { fontSize: clamp(2rem,4vw,2.5rem),   fontWeight: 700, lineHeight: 1.2,  letterSpacing: -0.015em }
  h2:            { fontSize: clamp(1.75rem,3vw,2rem),  fontWeight: 700, lineHeight: 1.3,  letterSpacing: -0.01em }
  h3:            { fontSize: 1.5rem,  fontWeight: 600, lineHeight: 1.4 }
  body-lg:       { fontSize: 1.0625rem, fontWeight: 400, lineHeight: 1.75 }
  body-md:       { fontSize: 0.9375rem, fontWeight: 400, lineHeight: 1.65 }
  body-sm:       { fontSize: 0.8125rem, fontWeight: 400, lineHeight: 1.6 }
  label-caps:    { fontSize: 0.75rem,  fontWeight: 600, letterSpacing: 0.08em }
  endorser:      { fontSize: 0.8125rem, fontWeight: 500, letterSpacing: 0.04em, opacity: 0.72 }  # "by Paradiso"
  stat-number:   { fontSize: 3rem, fontWeight: 800, letterSpacing: -0.04em }

rounded:  { xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 20px, 2xl: 24px, pill: 999px, modal: 18px }
spacing:  { 1: 4px, 2: 8px, 3: 12px, 4: 16px, 5: 24px, 6: 32px, 7: 48px, 8: 64px, 9: 96px, 10: 128px }
---

> **이 문서의 위치.** 리브랜드 *제안*용 Design.MD다. 승인되면 루트 `DESIGN.md`를 대체하고,
> 그때 `index.html`/`ai.html`/`new-home.html`의 브랜드 표기·테마·카피가 갱신된다.
> 승인 전까지 프로덕션은 변경하지 않는다(보존 계약: `docs/design/PARADISO_UX_DIRECTION_LOCK.md` §2).
> TDS 인용 근거는 업로드된 3개 파일:
> `consumer-ux-guide.md`(브랜딩·다크패턴·UX라이팅·그래픽·해상도),
> `ux-writing.md`(보이스톤 5원칙),
> `components.md`(TDS 컴포넌트 규율).

## 0. 전략 한 줄 (왜 이 구조인가)

"Paradiso가 비자 플랫폼으로 안 와닿는다"의 정답은 **이성 제품 / 감성 하우스 분업**이다.

- **Visable** = *Visa + -able + Visible*. 카테고리를 즉시 말하는 **이성(rational) 네임** → "안 와닿는다" 문제 해결.
- **Paradiso(Club Paradiso)** = 디아스포라→낙원 서사를 품는 **감성(emotional) 하우스** → 브랜드의 영혼 보존.
- **New Home** = 도착·정착이라는 **감성적 결과(outcome)** 제품.

전환은 *Branded House → House of Brands*. Paradiso는 제품 표면에서 한 칸 위(퍼블리셔)로 물러난다.

## 1. 네이밍 & 락업 (Lockup)

### 기본 락업: `Visable by Paradiso` (엔도스드 브랜드)
전환기 동안 기존 Paradiso 신뢰·검색 유입을 Visable로 이전하기 위해 **"by Paradiso" 엔도서 라인**을 함께 노출한다.

```
┌──────────────────────────┐
│   Visable                │  ← 워드마크: 800 / letter-spacing -0.02em
│   by Paradiso            │  ← endorser: 0.8125rem / 500 / opacity .72 (typography.endorser)
└──────────────────────────┘
```

- **단독 `Visable`** 은 협소 UI에서만 허용: 파비콘, 모바일 앱바(첫 화면 스크롤 이후), `<title>` 축약.
- **엔도서 노출 의무 영역**: 히어로, 푸터, About, 출처/면책 블록, 공유 OG 카드.
- **언어**: 워드마크는 라틴 `Visable` 고정(코인드 포트만토 — 한글 음차 "비자블" 미사용).
  - TDS는 브랜드명 한글 권장(`consumer-ux-guide.md` §1)이나, *고유 코인드 네임*이라는 명확한 사유로 라틴 유지.
  - **대신 항상 한글 디스크립터를 병기**: `Visable · 비자·체류 안내`.
- **금지**: `Paradiso 39`, `Visable 39`, 숫자 접미사 일체(`scripts/check_repo.sh` FORBIDDEN_REGEX 확장 필요).

### 제품별 락업 맵
| 제품 | 기존 | 신규 락업 | 비고 |
|---|---|---|---|
| 비자·체류 (`index.html`) | Paradiso | **Visable by Paradiso** | 마스터 → 제품으로 강등, 하우스로 엔도스 |
| 국적·귀화 (`new-home.html`) | Paradiso: New Home | **New Home by Paradiso** | 콜론 → "by" 엔도서 |
| AI (`ai.html`) | Waymaker by Paradiso | **Waymaker by Paradiso** (유지) | 두 제품 공통 진입 → 하우스 엔도스 유지 |
| 스튜디오/팀 | (없음) | **Club Paradiso** | 신규. About·하우스 서사·저작권 표기 |

## 2. 색 (Colors)

팔레트는 **하우스 공유**다. 제품 차이는 *hue가 아니라 baseline 온도·장식·밀도*로 만든다 — 팔레트 분열 방지.

- **Emerald(`#0EA37B`) 단일 강조 유지.** 화면당 ≤3. 강력한 기존 에쿼티이므로 보존.
- ⚠️ **토스 블루(`#3182F6`) 차용 절대 금지.** `consumer-ux-guide.md`는 파트너가 토스와 명확히 구분돼야 한다고 못박는다. 토스에서 가져오는 것은 *원칙*(명료성·정보위계·라이팅·다크패턴)이지 *자산*(컬러·로고·그래픽)이 아니다.
- **Visable 베이스** = `surface(#FCFAF5)` near-white → 더 깨끗·명료.
- **Paradiso-warm 베이스** = `neutral(#F4EEE0)` warm paper → 더 따뜻·서정.
- ⚠️ **WCAG**: Emerald + 흰 텍스트 = 3.21:1 (AA 미달). Primary 버튼은 `primary-deep(#085E48)` 배경 + `neutral` 텍스트(8.4:1, AAA). 이 규칙은 리브랜드와 무관하게 유지.

## 3. 타이포그래피

**Pretendard Variable 단독.** 신규 폰트 추가 금지(웹폰트 블로트 회피 — `CLAUDE_DESIGN_INTEGRATION_AUDIT.md` §7).
무게 위계(기존 픽스 유지): Hero 800 / Heading 700 / Strong 600 / Body 400. `font-weight: 900` 을 h2 이하에 금지.
`Visable` 워드마크는 800 / `-0.02em`, endorser는 `typography.endorser`. 한국어 본문 `word-break: keep-all; line-height ≥ 1.65`.

## 4. 레이아웃 & 밀도 (TDS 명료성 참조)

`components.md`/`consumer-ux-guide.md`의 *정보 위계·여백·컴포넌트 규율*을 Visable에 적용한다.

- **Visable(clarity-forward)**: 한 화면 = 하나의 주(主)행동. 정보 밀도 높은 섹션은 토스식으로 *그룹·여백·한 줄 위계*로 정돈. kitsch/브러시/아나그램 장식은 제품 표면에서 제거 → 하우스로 이동.
- **Paradiso-warm(editorial)**: 브러시 워드마크·아나그램·서정 여백 허용(About·New Home).
- 컨테이너 3종(narrow 720 / default 960 / wide 1180), 8pt 그리드, 터치 타겟 ≥44px 유지.
- **탭바를 쓸 경우**(`consumer-ux-guide.md` §3): 토스 권고대로 *플로팅 형태, 2~5개*. 단 이 앱은 미니앱이 아니므로 토스 전용 컴포넌트 의존이 아니라 동일 *형태 원칙*만 참조.
- **그래픽 규율**(`consumer-ux-guide.md` 그래픽): 한 화면 핵심 그래픽 1개, 문맥 적합, 장식 파티클·과한 그라데이션 금지, 라이트/다크 양쪽 가독 중간 명도. → 현 "kitsch 레이어"를 이 기준으로 다이어트.

## 5. UX 라이팅 — 토스 보이스톤 **하이브리드** (핵심)

`ux-writing.md` + `consumer-ux-guide.md`의 UX 라이팅 5원칙을 **UI·안내 레이어에 적용**하되, **법적 신뢰 레이어는 현 공식 톤을 보존**한다(CLAUDE.md 비협상 규칙: 면책·경고·불확실성·검토필요 고지를 약화 금지).

### 5.1 해요체·능동·긍정을 쓰는 곳 (토스 적용 ✅)
버튼, 라벨, 검색 힌트, 헬퍼 텍스트, 빈 상태(empty), 온보딩, 성공/완료 메시지, 토스트, 일반 안내.

| 토스 원칙 (출처) | 규칙 | Before → After 예 |
|---|---|---|
| 해요체 (`ux-writing.md` §1) | 모든 UI 문구 해요체 | "조회하십시오" → "찾아볼게요" |
| 능동형 (`§2`) | 수동·완료형 빼기 | "검색되었습니다" → "찾았어요" |
| 긍정형 (`§3`) | 없음/불가 → 가능 프레임 | "검색 결과가 없습니다" → "다른 키워드로 찾으면 나올 수 있어요" |
| 캐주얼 경어 (`§4`) | 과도한 '~시/께' 제거 | "입력해 주시겠어요?" → "상황을 적어주세요" |
| 명사+명사 풀기 (`§5`) | 한자어 풀어쓰기 | "체류자격 변경 신청 진행" → "체류자격을 바꾸려면" |
| 다이얼로그 (`§3 tip`) | 왼쪽 버튼 = **닫기**(취소 아님) | "취소 / 확인" → "닫기 / 확인" |

### 5.2 공식 톤을 **유지**하는 곳 (토스 미적용 🔒)
법적 면책, 공식 출처 경고, 자격·허가 비보증, 불확실성·검토필요 고지.
- 예: "최종 판단은 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요." — **원문 그대로**.
- 예: "Visable은 공식 정부 서비스가 아닙니다. 제공 정보는 참고용입니다." — 유지.
- 근거: civic·법적 인접 제품에서 면책의 *정밀한 레지스터*는 신뢰 장치다. 해요체로 가볍게 만들면 보호가 약화된다 → CLAUDE.md 위반.

> **요지**: 사용자를 *돕는* 말 = 해요체로 친근하게. 사용자를 *보호하는* 말 = 정확한 공식 톤으로.

## 6. 다크패턴 금지 (TDS, civic 제품에 특히 중요)

`consumer-ux-guide.md` 다크패턴 5종 — Visable은 신뢰가 생명이므로 **전부 강제**한다.

1. 진입 즉시 전면 바텀시트·알림동의 인터럽트 금지.
2. 뒤로가기 시 이탈 막는 바텀시트 금지.
3. 나갈 선택지 없는 강제 CTA 금지 — 항상 탈출구 제공.
4. 예상 못한 순간 전면 광고·인터럽트 금지.
5. **CTA는 다음 행동을 말한다**(`§5`). 버튼에 가치문구 반복 금지. "확인" 같은 모호한 라벨 대신 "서류 목록 보기", "절차 따라가기"처럼 *결과*를 적는다.

## 7. 컴포넌트 (TDS 규율 + 기존 매핑)

`components.md`의 원칙 — *커스텀 UI보다 일관된 소수 컴포넌트*. 기존 Paradiso 컴포넌트(button-primary/secondary/ghost, chip, visa-code-badge, visa-result-card, modal-box, search-bar, ai-answer-card, hikorea-banner 등)를 유지하되 Visable 테마에서 장식을 덜어낸다.

- **Visa Result Card** 스캔 순서 유지: ① 코드 배지+한/영 명칭 → ② 매뉴얼 도메인 배지 → ③ 절차 세그먼티드 → ④ 해당 절차 문서 → ⑤ 출처. 문서 전체를 한 화면에 쏟지 않는다.
- **HiKorea Banner**: 검색 결과 상단 상시 노출(`primary-deep` 배경 + `neutral` 텍스트).
- **포커스 링**: `:focus-visible` 시 `0 0 0 3px rgba(14,163,123,0.35)`.
- **모달 진입**: `scale(0.97)→scale(1)`, `200ms ease-out`.

## 8. 마이그레이션 맵 (브랜드 표기 교체 지점)

> 모두 *표기·카피·테마* 변경. **마크업 구조·`id`·`data-action`·인라인 스크립트·`window.PARADISO_*` 식별자는 보존**(UX Direction Lock §2). 코드 식별자의 `PARADISO_` 접두사는 *바꾸지 않는다* — 사용자 표면 문자열만 교체.

| 위치 | 표면 문자열 변경 | 코드 식별자 |
|---|---|---|
| `index.html` `<title>` | `Paradiso` → `Visable · 비자·체류 안내` | — |
| 히어로 워드마크 | 브러시 `Paradiso` → set-type `Visable` + `by Paradiso` | `assets/brand/` 신규 워드마크 자산 필요 |
| 히어로 eyebrow/마퀴 | "Paradiso · Korea residence guide" → "Visable · 비자·체류 안내" | — |
| 아나그램 + brandStory | **제품에서 제거 → About/하우스(Club Paradiso) 섹션으로 이동** | `#anagram` id는 이동 후에도 의미적 위치 유지 |
| 푸터 워드마크/면책 | `Paradiso` → `Visable by Paradiso` (면책 본문 톤 유지) | `.ft-logo` |
| `new-home.html` h1 | `Paradiso: New Home` → `New Home by Paradiso` | `data-c="hero.title"` |
| `ai.html` 타이틀/말풍선 | `Waymaker by Paradiso` (유지) | `window.PARADISO_BACKEND_URL` 등 유지 |
| `package.json`/메타 | 필요 시 name/description | 빌드 영향 확인 |
| `scripts/check_repo.sh` | FORBIDDEN_REGEX에 `Visable 39` 등 추가 | — |

## 9. Do & Don't

### Do
- `Visable by Paradiso` 엔도서를 히어로·푸터·About·출처에 노출.
- 한글 디스크립터 병기(`Visable · 비자·체류 안내`).
- UI·안내 = 토스 해요체·능동·긍정 / 면책·경고 = 현 공식 톤(하이브리드).
- 다크패턴 5종 전면 차단, CTA에 *결과* 적기.
- 아나그램·브러시·서정은 하우스(Club Paradiso)/New Home에만.
- Emerald 단일 강조, 화면당 ≤3. WCAG는 `primary-deep`+`neutral`.
- 보존 계약 준수: `id`·`data-action`·인라인 스크립트·`PARADISO_` 식별자 유지.

### Don't
- **토스 블루(`#3182F6`)·토스 로고·토스 그래픽 자산 차용 금지** — 파트너 구분 원칙.
- 면책·공식출처 경고·불확실성 고지를 해요체로 가볍게 만들기 금지.
- 숫자 접미사(`Visable 39`) 금지.
- 코드 식별자(`PARADISO_BACKEND_URL` 등) 리네임 금지 — 표면 문자열만 교체.
- 마크업 구조·`<body class="landing" data-theme="light">`·메인 `<script>` 바이트 보존 위반 금지.
- 신규 웹폰트·React/Babel·새 외부 런타임 추가 금지.
- Visable 제품 표면에 아나그램·kitsch 장식 잔존 금지(하우스로 이동).

## 10. 남은 결정 (출시 전)
- **상표**: `Visable` KIPRIS(한국) 9·35·42류 검색 1회 권장. 유럽 Visable(B2B 무역)과 업종·지역 상이로 충돌 가능성 낮으나 확인.
- **Waymaker 엔도스**: 현재 하우스(by Paradiso) 유지. 추후 Visable 전속으로 좁힐지 재논의.
- **도메인/SNS 핸들**: visable.* 가용성 확인.
