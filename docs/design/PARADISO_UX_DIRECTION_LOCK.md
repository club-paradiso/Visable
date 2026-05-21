# Paradiso UX Direction Lock

**작성일:** 2026-05-21
**대상 저장소:** `lucanomics/Paradiso` (`main`, HEAD `8022b7f` / PR #110 머지 상태)
**Figma 참조:** Figma Make `N695iXnoavEOSHITttdCCu` (“Paradiso 후보”)
**상태:** Railway 백엔드 URL 검증 미해결 — 본 문서는 백엔드 가용성에 의존하지 않음(Lock 진행)

-----

## 0. 접근 가능성 실측 (먼저 확인한 것)

작업 전제부터 검증했다. 프롬프트에 적힌 전제 중 일부는 실제 저장소 상태와 달랐고, 아래는 추측이 아니라 직접 확인한 사실이다.

|대상                            |결과                                                                                     |확인 방법                                           |
|------------------------------|---------------------------------------------------------------------------------------|------------------------------------------------|
|Figma Make 파일 직접 fetch        |**차단** (robots.txt)                                                                    |web_fetch                                       |
|Figma MCP `get_design_context`|**부분 성공** — 소스 트리/컴포넌트명은 획득, 파일 *내용*은 “Resource links are not currently supported”로 미반환|Figma MCP                                       |
|GitHub 저장소 클론 (`main`)        |**성공** — 성숙한 풀스택 상태 확인                                                                 |git clone                                       |
|PR #103 / #104                |**실재 확인** (날조 아님)                                                                      |`docs/audits/POST_PR_95_106_MAIN_STATE_AUDIT.md`|

**정정 1 — Figma Make 내용 직접 판독 불가.** MCP가 반환하는 것은 파일 매니페스트(컴포넌트명·이미지 해시)뿐이고, `App.tsx`·`theme.css`·`HeroGateway.tsx` 등의 실제 코드/스크린샷은 못 읽는다. 이는 §11.6에 기록된 과거 Claude Code 인스턴스가 겪은 한계와 **동일**하다. 따라서 “Figma를 1차 비주얼 참조로 쓰라”는 지시는 *부분적으로만* 이행 가능하다. 컴포넌트 아키텍처는 알 수 있으나 픽셀·색·간격의 캐노니컬 출처는 Figma가 아니라 저장소 안에 이미 인코딩된 `index.html`의 “FIGMA PIXEL-PERFECT LAYER”다.

**정정 2 — 저장소는 프롬프트가 암시한 것보다 훨씬 성숙하다.** GitHub 웹 페이지는 한때 2커밋·템플릿 상태로 표시됐으나, 실제 `main` 클론은 FastAPI 백엔드(`backend/paradiso_backend.py`), 752KB 단일 파일 `index.html`, `ai.html`, 광범위한 `docs/`, 그리고 Figma Make 익스포트가 통째로 보존된 `docs/archive/figma-make-vite-before-migration/`을 포함한다. 즉 Figma 핸드오프 문서 전부가 디스크에서 판독 가능하다.

**정정 3 — Figma Make 파일은 `/make/` URL이지만 MCP로 접근됐다.** 단지 내용 반환이 막혔을 뿐이다. nodeId를 어떤 값으로 넣어도 동일한 매니페스트만 돌아온다.

-----

## 1. Figma 개념에서 추출한 UX 방향 (장식 복제가 아니라 구조)

Figma Make 매니페스트가 노출한 컴포넌트 트리는 그 자체로 정보 설계의 의도를 드러낸다. 실재가 확인된 컴포넌트는 다음과 같다(모두 매니페스트 실측):

`HeroGateway` · `StatBridge` · `FeatureTrust` · `AnagramBrandStory` · `StartSection` · `ValuesSection` · `RoadmapSection` · `FooterCTA` · `KeywordsHints` · `Landing` · `routes`.

이 명명에서 읽어낼 수 있는 랜딩 서사 구조:

1. **HeroGateway** — 입구(검색·진입). “관문”이라는 단어 선택이 핵심: 히어로는 장식이 아니라 *기능적 게이트웨이*다.
1. **StatBridge** — 신뢰 수치로 히어로와 본문을 잇는 다리.
1. **FeatureTrust** — 기능 소개를 *신뢰* 프레임으로 묶음(공공서비스 톤).
1. **AnagramBrandStory** — 브랜드 서사(Paradiso 아나그램).
1. **StartSection → ValuesSection → RoadmapSection** — 시작 유도 → 가치 → 로드맵.
1. **FooterCTA** — 최종 행동 유도.
1. **KeywordsHints** — 검색 키워드 힌트(검색 진입 보조).

**추출한 방향(구현 대상):** Figma의 *시각*이 아니라 이 *서사 골격*을 가져온다. 현재 `index.html`의 `.landing-scroll` 섹션 순서(Brand → Feature → Pathways → How-it-works → Sources → Tools → Agent finder → About → CTA)와 매핑하면, Figma는 “기능 나열”을 “신뢰 서사”로 재구성하라고 말하고 있다. 이것이 베껴야 할 핵심이다.

-----

## 2. 절대 보존 계약 (PR #104 — 깨면 앱이 죽는다)

PR #104 = `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` §10. UX 작업이 이 선을 넘으면 12,887줄 단일 파일 앱의 동작이 깨진다. 새 마크업·CSS는 다음을 **반드시** 지킨다(원문 §10 직접 인용 근거):

1. `§2.8`의 모든 `id`를 같은 의미적 위치에 유지.
1. 정적 `data-action`을 버튼/링크 요소에 유지(중앙 위임 핸들러가 47개 값을 디스패치).
1. 인라인 `onclick` 2개(`startPreEntryTrack()`, `startInKoreaTrack()`)를 visa-track-card에 유지.
1. 초기 상태 `<body class="landing" data-theme="light">` 유지.
1. JS 렌더 트리거의 `data-vcode`/`data-type`/`data-subidx` 유지.
1. `<head>` 끝의 2줄 config 스크립트(`window.PARADISO_BACKEND_URL`) 유지.
1. `<body>` 끝의 메인 `<script>`(8253–12885줄) **바이트 단위 보존**.
1. favicon·Pretendard CDN·`<title>`·`<meta theme-color>` 유지.
1. `<canvas id="starCanvas">`를 `<body>` 직속·`#hero` 앞에 유지.
1. `<header id="hero">` 유지(스포트라이트 IIFE가 `getElementById('hero')` 호출).

**상태 머신(절대 변경 금지):** body 클래스 `landing` → `searching` → `searched`(+ 전환 `anagram-run`/`launching`). 현재 CSS에 `:not(.searched)` 셀렉터가 49회 등장하며 랜딩↔결과 레이아웃을 가른다. `body.searched`는 JS가 제어하는 클래스이므로 그대로 둔다.

**다크모드 규칙:** `[data-theme="dark"]`를 `<body>`에 거는 `toggleTheme()` 방식. `@media (prefers-color-scheme)`로 바꾸면 사용자 토글이 OS 설정에 묻힌다 — 금지.

-----

## 3. 캐노니컬 디자인 토큰 (PR #103 파리티 레이어 = 출처)

아래 값은 `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` §5에서 그대로 가져온 실측값이다. Figma에서 추정한 것이 아니라 이미 코드에 인코딩된 캐노니컬 토큰이다. UX Lock은 이 토큰을 단일 출처로 고정한다.

**브랜드 컬러**

- `--emerald: #0EA37B` (primary CTA), `--emerald-deep: #085E48`, `--emerald-hover: #0c8c69`
- `--coral-bright: #FF6B5B` (accent), `--coral-deep: #E0513E` (error)
- `--amber-warn: #E68A3A` (warning)

**중립 — 따뜻한 종이+잉크 (공공서비스 톤의 핵심)**

- 배경 `--paper: #F4EEE0`, 결과면 `--paper-surface: #FBF5E6`
- 잉크 `--ink: #0E1F1A`, 뮤트 `--ink-muted: #7A8580`, 라인 `--line: #C9BFA5`
- 글래스 `--glass-bg: rgba(255,255,255,.13)`, `--glass-blur: 20px` (히어로 검색면)

**타이포** — `--ff: "Pretendard Variable"` 기반. 스케일 `--fs-base: 15px` / `--fs-md: 17px` / `--fs-2xl: 32px`.

**간격(8pt 그리드)** — `--sp-2:8 / --sp-4:16 / --sp-5:24 / --sp-6:32 / --sp-7:48 / --sp-9:96`.

**컨테이너** — narrow `720px`(히어로 카피·브랜드 서사) / default `960px`(대부분 섹션) / wide `1180px`(결과 리스트·푸터 CTA) / gutter `clamp(1rem,4vw,2rem)`.

-----

## 4. 결과 카드 정보 위계 (Lock — `MANUAL_BASED_INTERFACE_REBUILD_REVIEW.md` 기준)

이전 결과 UI는 평면적 법률 메모였다. 코드 위계가 안 보였고, 발급/체류 절차가 분리되지 않았고, 서브코드를 본문에서 추론하게 만들었다. 시민기술 제품에서 이는 회피 가능한 리스크다. 재설계된 스캔 경로를 고정한다:

1. 베이스 코드 + 한/영 명칭
1. 매뉴얼 도메인 배지(사증발급 / 체류민원 / 공통)
1. 검증·리뷰 배지(2026.5 매뉴얼 상태)
1. 명시적 서브코드 섹션(컴팩트 카드)
1. 절차 컨트롤(세그먼티드)
1. 절차별 문서 그룹(선택된 절차만 노출)
1. 공통 경고 박스
1. 출처 참조 블록
1. 선택적 액션(모달·AI 분석)

**스캔 경로:** 비자 식별 → 절차 선택 → 해당 절차 문서만 읽기 → 주의·출처 확인. 문서를 한 화면에 다 쏟지 않는다.

**모바일:** 단일 컬럼, 가로 오버플로 금지. 절차 탭은 자체 행 안에서만 가로 스크롤. 한글은 `word-break: keep-all` + 가독 line-height.

**접근성:** 절차 버튼 활성/비활성 상태 시각화, 비활성 절차는 뮤트하되 이해 가능, 색에만 의존 금지(라벨이 의미를 운반), 네이티브 버튼으로 키보드 도달 유지.

-----

## 5. 컴포넌트 스펙 요약 (§6 — 새 CSS가 제공해야 할 것)

§2.9의 모든 클래스는 JS innerHTML에서만 등장하더라도 새 CSS가 스타일을 제공해야 한다. 새 디자인 언어가 JS 렌더 카드/행/배지의 *유일한* 스타일 출처이기 때문이다.

- **버튼** `.btn` — `min-height:44px`, `border-radius:var(--r-md)`, `:focus-visible`에 `--focus-ring`, `:active`에 `translateY(1px)`. `.btn-primary`는 emerald 배경.
- **탭** — 세그먼티드, 활성/비활성 명시 상태(절차 컨트롤에 직결).
- **배지·칩** — 도메인/리뷰 배지(§4의 위계 2·3번).
- **모달** — AI/직업코드/관할/문서/FAQ 5종, 기존 트리거 보존.
- **하이라이트** `<mark class="h">` — 검색어 강조.
- **내비** `#topCtrls` — 언어·테마·도시 컨트롤.

-----

## 6. 히어로 레이아웃 (§7.1 — HeroGateway 매핑)

- 분위기: SVG 수평선 배경 + 포인터 추종 emerald 스포트라이트(`--mx`/`--my`를 IIFE가 세팅 — 동작 유지 필수).
- 수직 리듬: 상단 패딩 `clamp(4rem,8vh,6rem)`, 하단 `--sp-7`.
- 중앙 컬럼 `max-width: var(--container)`.
- 워드마크 높이 `clamp(72px,9vw,128px)`.
- 진입 레일(버튼 2개): 태블릿+ `grid-template-columns:1fr 1fr; gap:var(--sp-4)`, 모바일 스택.

**모바일 우선:** 기본 390px(iPhone 13 mini), <480px 단일 컬럼, 768px부터 2컬럼, 1024px부터 3컬럼+. 터치 타겟 최소 44px. `prefers-reduced-motion` 존중(스포트라이트·캔버스·리빌 애니메이션).

-----

## 7. 구현 순서 (백엔드 비의존, 즉시 착수 가능)

순서대로 진행한다. 각 단계는 §2 보존 계약 안에서만 움직인다.

1. **토큰 고정** — §3 캐노니컬 `:root` 블록을 단일 출처로. 레거시 이름은 alias로 새 값에 연결(전환 중 JS 렌더 HTML이 깨지지 않게).
1. **결과 카드 위계** — §4의 9단계 anatomy를 JS 템플릿 클래스에 맞춰 CSS만으로 구현. 마크업 구조·`data-*` 불변.
1. **히어로/랜딩 리듬** — §6 + Figma 서사 골격(§1)으로 `.landing-scroll` 섹션 정렬.
1. **접근성 패스** — 포커스 링, 탭 상태, 색 비의존 라벨, 키보드 도달.
1. **모바일 390px 검증** — 환경상 브라우저 실행 불가. 푸시 후 Luca가 실기기/DevTools로 확인(§11.7).

-----

## 8. 미해결·확인 필요 (DATA MISSING 포함)

- **Figma 최신 상태 정렬** — 현재 픽셀 파리티 레이어보다 *새로운* Figma 상태에 맞추려면 (a) Make 파일의 구체적 nodeId 제공, (b) `theme.css`/컴포넌트 `.tsx` 내용 붙여넣기, (c) “픽셀 파리티 레이어를 출처로 인정” 중 택1 필요. **현재 기본값: (c).**
- **시민 인용 검증 성숙도** — 백엔드 citation verifier는 `CITATION_VERIFICATION_NOT_WIRED` 의미가 남은 *부분 배선* 상태(POST_PR_95_106 §2.6). UI가 “법적으로 검증됨”을 기본 과대주장하지 않도록 §4의 리뷰 배지 카피를 보수적으로.
- **Railway URL** — 미검증. 단 `loadVisaData()`가 정적 JSON 폴백을 가지므로 UX Lock·랜딩·결과 렌더는 백엔드 없이 동작. **차단 요인 아님.**
- **DATA MISSING:** Figma Make 내부의 실제 색/간격이 §3 토큰과 1:1로 일치하는지 여부는 MCP가 내용을 반환하지 않아 *직접 대조 불가*. §3은 저장소 인코딩값을 출처로 삼은 것이며 Figma 원본과의 픽셀 동일성은 미검증.

-----

## 9. 한 줄 결론

Figma는 **서사 골격**(HeroGateway→StatBridge→FeatureTrust→…→FooterCTA)을 제공하고, 저장소의 **픽셀 파리티 레이어**가 색·간격·컴포넌트의 캐노니컬 출처다. UX Lock은 이 둘을 결합하되, PR #104 보존 계약(§2)을 절대선으로 두고 CSS·정보위계만 움직인다. 백엔드 비의존으로 1~4단계 즉시 착수 가능.
