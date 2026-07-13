# Paradiso — Figma 작업 인수인계 (→ Codex Desktop)

> 이 문서 하나만 Codex Desktop에 붙여넣으면 지금까지의 Figma 작업을 그대로 이어갈 수 있습니다.
> 아래 **§0 붙여넣기용 프롬프트**를 통째로 복사해서 시작하고, 나머지 섹션은 참조 자료입니다.

---

## §0. 붙여넣기용 시작 프롬프트 (이 블록을 그대로 Codex에 붙여넣기)

```
당신은 Paradiso(한국 비자·체류 정보 플랫폼)의 Figma 디자인 작업을 이어받습니다.
세 개의 서비스 표면 — Visable(허브), Waymaker(AI 동행), New Home(국적·귀화) — 의
"Aurora Live" 히어로 시안을 편집·정리하는 일입니다.

■ 작업 대상 Figma 파일
- fileKey: pInhK8Oyg04lpL4PMSCB4l
- 편집은 반드시 Figma MCP의 use_figma(플러그인 API/JS 실행)로 합니다.
- use_figma를 호출하기 전에 반드시 figma-use 스킬(또는 skill://figma/figma-use/SKILL.md
  리소스)을 먼저 로드하세요. 안 하면 폰트/레이아웃 관련 버그가 납니다.

■ 절대 규칙 (매우 중요)
1. 히어로 카피(헤드라인/서브카피)는 오너가 직접 관리합니다. 요청 없이 문구를 바꾸지 마세요.
2. 각 히어로 페이지에는 애니메이션용 프레임이 여러 개 있습니다. "① State 1 · MASTER"
   프레임에서만 편집하고, State 2·3·4는 오로라 배경 루프(Smart Animate)용 복제본입니다.
   ★ MASTER를 수정하면 반드시 같은 수정을 State 2·3·4에도 동일하게 반영해야 배경
   애니메이션이 어긋나지 않습니다. (아래 노드 ID 표 참고)
3. 배포된 실제 사이트(index.html)는 이 작업에서 직접 건드리지 않습니다. Figma가 먼저입니다.
4. 리걸/이민 관련 문구·면책·출처 경고는 임의로 추가·삭제·약화하지 마세요.

■ 먼저 할 일
1. figma-use 스킬 로드 → use_figma로 파일 페이지 목록 읽기(read-only)로 현재 상태 확인.
2. 아래 "노드 ID 지도"로 편집 대상 프레임을 특정.
3. 변경 후 반드시 get_screenshot으로 시각 검증하고, MASTER↔State 동기화를 확인.

작업 지시는 이후 별도로 전달됩니다. 위 규칙을 지키며 진행하세요.
```

---

## §1. 파일 개요

- **fileKey**: `pInhK8Oyg04lpL4PMSCB4l`
- 스택(참고): 실제 프로덕트는 vanilla HTML/CSS/JS 단일 파일(`index.html`, 저장소 루트). Figma는
  디자인 소스이며 프로덕션 코드와 자동 동기화되지 않습니다.
- 디자인 언어: "Cinematic Aurora" — 따뜻한 종이/이멀랄드 톤, periwinkle 스크립트 워드마크,
  투톤 헤드라인, liquid-glass 그라디언트 보더, 하단 kinetic 마퀴, 우측 무드 도트 내비.
- 폰트: **Inter** (이 환경은 Inter에 한글 폴백이 있어 한글도 Inter로 렌더됨).
  쓰는 스타일: `Regular`, `Medium`, `Semi Bold`, `Bold`. (주의: "Semi Bold" — 띄어쓰기 있음)
- 핵심 브랜드 컬러: periwinkle `#7F89CE` = `{r:0.498, g:0.537, b:0.808}` (0–1 범위).

---

## §2. 페이지 목록 (30개)

| # | 이름 | page node id |
|---|------|--------------|
| — | ✦ Cover | `63:2` |
| 00 | README · 작업 방식 (START HERE 보드 = `3:10`) | `3:2` |
| 01 | Brand · Tokens · Logo | `3:3` |
| 02 | Components · Editable Patterns | `3:4` |
| 03 | Visable Landing | `3:5` |
| 04 | Background System · Aurora Mesh | `3:6` |
| 05 | Waymaker New Home · Product Surfaces | `3:7` |
| 06 | Prototype Map · User Flow | `3:8` |
| 07 | Handoff · Implementation Notes | `3:9` |
| 08 | Website Draft · Full Screens | `6:2` |
| 09 | **Design System · Components** (로고·버튼·오로라 컴포넌트) | `14:2` |
| 10 | Website Draft · Mobile | `21:2` |
| 11 | Rebrand Workspace | `39:2` |
| 12 | Proposal · P0-c 검색→결과 | `81:4` |
| 13 | Proposal · 시그니처 3막 | `91:8` |
| 14 | **Review · 검토 & 피드백** (수정요청 여기) | `103:4` |
| 15 | Proposal · Visable 데스크톱 풀 결과 | `109:4` |
| 16 | Proposal · New Home 준비상태 체크 | `115:4` |
| 17 | Proposal · 테마 시스템(라이트/다크) | `118:4` |
| 18 | Proposal · New Home 데스크톱 풀 랜딩 | `121:4` |
| 19 | Proposal · Waymaker 라이트 변형 | `124:4` |
| 20 | Proposal · 상태 세트(에러·빈·로딩) | `125:4` |
| 21 | Proposal · 반응형 브레이크포인트 | `127:4` |
| 22 | Proposal · Visable 랜딩(검색 전) | `129:4` |
| 23 | Proposal · 서류 체크리스트 | `133:4` |
| 24 | Proposal · New Home 다크 랜딩 | `135:4` |
| 25 | Proposal · i18n 대역(한·영·중) | `137:4` |
| 26 | Proposal · 아이콘·일러스트 세트 | `138:4` |
| 27 | **Proposal · Visable 히어로 (Aura)** | `142:4` |
| 28 | **Proposal · New Home 히어로 (Aurora Live)** | `194:4` |
| 29 | **Proposal · Waymaker 히어로 (Dark Aurora)** | `198:4` |

> 페이지의 `children.length`가 0으로 보이면 그건 Figma의 지연 로딩 때문입니다. 실제 내용을
> 보려면 `await figma.setCurrentPageAsync(page)`로 그 페이지로 전환해야 합니다.

---

## §3. 히어로 노드 ID 지도 (편집의 핵심)

세 히어로가 최종 시안입니다. 각 페이지는 Figma **Section**으로 묶여 있고, 그 안에
MASTER + 애니메이션 State 복제본이 세로로 쌓여 있습니다.

### 27 · Visable 히어로 — page `142:4`
- Section `211:12` "🎬 Visable Hero · Aurora Live" ← 편집 대상들이 여기
  - **MASTER** `142:5` (편집 여기) · PNG@2x export 설정됨 · flow 시작점
  - State 2 `190:51` / State 3 `190:109` / State 4 (황혼 Dusk) `190:167`
- Section `211:13` "🗒 작업 노트 · export 제외" ← 참고용 노트(`153:4`) + 결정 보드(`190:10`)

### 28 · New Home 히어로 — page `194:4`
- Section `214:20` "🎬 New Home Hero · Aurora Live"
  - **MASTER** `194:5` (편집 여기) · PNG@2x · flow 시작점
  - State 2 `196:4` / State 3 `196:46` / State 4 (황혼 Dusk) `196:88`

### 29 · Waymaker 히어로 — page `198:4`
- Section `214:33` "🎬 Waymaker Hero · Dark Aurora"
  - **MASTER** `198:5` (편집 여기) · PNG@2x · flow 시작점
  - State 2 `199:18` / State 3 `199:58`

> **State 복제본은 각 State가 다음 State로 넘어가는 Smart Animate reaction(AFTER_TIMEOUT)을
> 갖고 있습니다.** Visable/New Home은 마지막 Dusk에서 정지(휴식), Waymaker는 마지막에서 State 1로
> 루프백. reaction/flow는 노드 ID에 묶여 있으므로 리네임·재부모화(섹션 이동)로는 안 깨지지만,
> State 프레임을 새로 만들거나 삭제/detach하면 깨집니다.

### 로고 컴포넌트 (page 09 = `14:2`)
- `14:8` Logo / Visable Wordmark
- `203:13` Logo / New Home Wordmark
- `204:13` Logo / Waymaker Wordmark
- `205:17` Logo / Club Paradiso Wordmark
- 그 외: `Button` 컴포넌트 세트(`26:22`, Primary/Secondary × 상태 × Light/Dark),
  `Aurora / Animated` 컴포넌트 세트(`17:13`, State=A/B/C). 로컬 변수 컬렉션은 없음(색은 직접 값).

---

## §4. MASTER ↔ State 동기화 절차 (반드시 지킬 것)

MASTER(State 1)에서 텍스트/색/간격 등을 바꿨다면, **똑같은 변경을 그 페이지의 모든 State
복제본에 반복 적용**해야 합니다. 각 State는 텍스트 노드 이름이 MASTER와 동일하므로, 이름 또는
상대 경로로 찾아 같은 값을 세팅하면 됩니다.

권장 패턴 (예: 서브카피 문구를 세 State 모두에 반영):
```js
// figma-use 스킬 로드 후 실행
const page = await figma.getNodeByIdAsync("198:4"); // 해당 히어로 페이지
await figma.setCurrentPageAsync(page);
const frameIds = ["198:5","199:18","199:58"];       // MASTER + 모든 State
async function setText(node, text){
  const segs = node.getStyledTextSegments(['fontName']);
  for (const s of segs) await figma.loadFontAsync(s.fontName); // 현재 폰트 로드 필수
  node.characters = text;
}
for (const id of frameIds){
  const f = await figma.getNodeByIdAsync(id);
  const node = f.findOne(n => n.type==="TEXT" && n.name==="함께 정리하기"); // 노드 이름으로 특정
  if (node) await setText(node, "새 문구");
}
return { done: frameIds };
```

---

## §5. 지금까지 완료된 작업 (2026-07 세션 기준)

1. **작업 환경 정비**: 세 히어로를 Section으로 묶고, State 1을 "MASTER — 여기서 편집"으로
   리네임, 마스터에 PNG@2x export 설정 추가. Visable의 작업용 스캐폴드(노트/결정보드)는
   "export 제외" 섹션으로 격리.
2. **START HERE 가이드**: 00 README 페이지의 보드(`3:10`)를 실제 편집/내보내기 가이드로 재구축
   (① 편집하는 법 ② 내보내는 법 ③ 페이지 지도). ADHD 친화적으로 쉬운 문장·번호 단계로 서술.
3. **카피**: 오너가 히어로 헤드라인을 직접 최종 확정함 → 어시스턴트는 문구를 건드리지 않음.
4. **언어 버튼**: 헤더의 이진 토글 "한 / EN" → `🌐 KO`(아이콘+코드)로 세 히어로 11개 프레임 전체
   변경. 실제 사이트는 15개 언어 드롭다운이라 이진 토글이 오해를 줬기 때문(§6 참고).
5. **버튼 폭·간격 정합성 정리** (세 히어로 MASTER+State 전체):
   - 헤더 pill 높이 통일: 32→34px (상하 패딩 8→9).
   - 테마 아이콘 pill을 42×34 고정 크기·중앙정렬로 (해/달 이모지 폭 차이로 버튼이
     들쭉날쭉하던 문제 — New Home State 4 Dusk 포함).
   - 히어로 콘텐츠 세로 간격 통일: 18→20px.
   - Waymaker 검색바(prompt-bar) 높이 68→74px (Visable 검색창과 동일).
   - Waymaker CTA 텍스트–화살표 간격 6→8px (Visable/New Home과 동일).
6. **Visable 게이트웨이 카드 구조 버그 수정** (마스터+State 4개 전부):
   - 1행 카드 3개의 본문 텍스트가 카드 밖에 떠 있던 것을 카드 안으로 재부모화(위치 동일 유지).
   - "Waymaker by Paradiso" 카드에 완전 중복된 본문 노드가 겹쳐 있던 것 삭제.

---

## §6. 실제 배포 사이트 참조 (index.html)

- 파일: 저장소 루트 `index.html` (단일 파일, ~2만2천 줄).
- 지원 언어 15개 (`LANGUAGE_OPTIONS`, ~line 21849): 한국어·English·简体中文·繁體中文·
  日本語·Tiếng Việt·Tagalog·Bahasa Indonesia·Русский·Français·Español·العربية·Deutsch·
  Türkçe·Українська. 헤더 언어 버튼은 `🌐 KO 한국어` 드롭다운이며 모바일에선 국가명 숨김(`🌐 KO`).
- 테마: light 3무드 + dark "Dusk", `archive_diary` 에디토리얼 테마 등. 히어로의 4-State 무드가
  이 라이트↔Dusk 흐름을 표현.
- 카피/문구를 Figma에 반영할 땐 이 파일을 정본으로 참고(단, 오너 승인 없이 리걸 문구 변경 금지).

---

## §7. figma-use 필수 규칙 (자주 밟는 지뢰)

- **use_figma 호출 전 figma-use 스킬 로드 필수.** `skillNames`에 `resource:figma-use` 전달.
- 결과는 반드시 `return`으로 반환(객체/배열 OK). `console.log`/`figma.notify()` 안 됨.
- 색은 **0–1 범위** `{r,g,b}` (255 아님). paint `color`에 `a` 필드 넣지 말 것(투명도는 paint의
  `opacity`).
- **텍스트 편집 전 폰트 로드 필수**: 기존 노드는 `getStyledTextSegments(['fontName'])`로 현재
  폰트를 로드한 뒤 `characters` 변경. 안 하면 "unloaded font" 에러.
- 페이지 전환은 `await figma.setCurrentPageAsync(page)` (동기 setter 안 됨). **한 use_figma
  호출당 setCurrentPage는 1회만.** 여러 페이지 작업은 페이지별로 use_figma를 병렬 호출.
- `resize()`는 auto-layout sizing을 FIXED로 리셋함 → resize 후에 sizing 모드 재설정.
- `layoutSizingHorizontal/Vertical = 'FILL'`은 auto-layout 부모에 `appendChild` 후에 설정.
- **Section**: `appendChild` 시 자식은 절대좌표 유지(섹션 로컬 원점은 canvas 0,0). 섹션 원점을
  옮기면 자식이 함께 끌려감 → 원점 이동 시 자식 로컬좌표를 보정하거나, 원점은 두고 크기만
  키워 자식을 감싸는 방식 권장.
- 스크립트가 에러나면 원자적으로 롤백됨(부분 적용 없음). 에러 메시지 읽고 고친 뒤 재시도.
- 만든/바꾼 노드 ID는 항상 `return`으로 돌려받기.

---

## §8. 남은/후속 후보 작업 (선택)

- 초기 탐색 제안 페이지(12–26)는 아직 정밀 폴리시를 안 한 상태 — 필요 시 히어로와 동일한
  버튼/간격 기준으로 정리 가능.
- 헤더 언어 버튼을 데스크톱에서 국가명까지(`🌐 KO 한국어`) 노출하는 풀 버전으로 갈지 결정 필요
  (그럴 경우 옆 테마 토글과의 간격 재조정 필요).
- 전략 문서(PR #537)의 3막 카피와 실제 히어로 카피가 오너 수정으로 달라진 부분 — 전략 문서
  동기화 여부는 오너 판단.
- README(00)의 페이지 지도/가이드는 위 구조 변경을 이미 반영. 추가 구조 변경 시 함께 갱신.
