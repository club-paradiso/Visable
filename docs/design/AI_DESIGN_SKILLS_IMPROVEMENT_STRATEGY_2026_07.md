# AI 디자인 스킬 활용 개선 전략 — Visable · New Home · Waymaker

**작성일:** 2026-07-09
**대상 표면:** `index.html`(Visable) · `new-home.html`(New Home) · `ai.html` + `assets/js/waymaker-navigator.js`(Waymaker)
**출처 자료:** [trenddalkak] "에이전트 스킬 라이브러리 오픈소스 공개 — AI 디자인 스킬 75개"
(Meng To / Design+Code, `github.com/MengTo/Skills`)
**성격:** 디자인·프로세스 개선 *제안*. 확정 시 표면별 개별 PR로 분리 착수. 데이터·법률 콘텐츠 무관.

---

## 0. 한 줄 전략

> Meng To의 75개 AI 디자인 스킬을 **선별 도입**한다.
> **크래프트를 올리는 "프로세스" 스킬은 채택**하고, **장식을 더하는 "데코" 스킬은 거부**한다.
> 그리고 세 표면의 성격 — **Visable(이성·명료) / New Home(감성·서정) / Waymaker(과업·안내)** — 에
> 맞춰 같은 스킬을 서로 다른 강도로 적용한다.

이 전략의 핵심은 "AI 스킬을 얼마나 쓰느냐"가 아니라 **"무엇을 거부하느냐"** 다.
Paradiso는 시민·법률 인접 신뢰 제품이고, 신뢰는 절제에서 나온다.

---

## 1. 노션 소스 분석 — 무엇이 공개됐나

| 항목 | 내용 |
|---|---|
| 정체 | Meng To(Design+Code 창업자, Aura 제작자)가 오픈소스로 공개한 **Agent Skills 라이브러리** |
| 규모 | 스킬 75개. `Claude Code`·`Cursor`·`Codex`에서 `SKILL.md`를 붙여넣어 사용 |
| 카테고리 | `web-design` 62 · `codex` 10 · `ui` 1 · `media` 2 |
| 커버리지 | 랜딩페이지, 애니메이션/모션, WebGL, CSS 효과, 레이아웃, UI 프롬프트, 이미지 소싱 |
| 제작자 추천 "베스트 4" | `video-to-superprompt`(영상→프롬프트), `html-to-interaction-prompts`(HTML→인터랙션 스펙), `stitched-full-page-capture`(전체 페이지 스티치 캡처), `daily-ui-inspiration-capture`(개인 저장소 전용, 재현 난이도 높음) |
| 권장 파이프라인 | 스킬로 프롬프트 추출 → **Fable 5**(claude.ai 모델 선택)로 실제 결과물 생성 |

### 1.1 핵심 통찰 (그리고 함정)

이 라이브러리는 62/75가 `web-design` — 즉 **마케팅 랜딩페이지·모션·WebGL 플래시** 지향이다.
Meng To의 미학은 화려하고 감각적이다(Aura의 그라데이션·글로우가 대표). 이것은 스타트업 랜딩엔 강력하지만,
**Visable/New Home/Waymaker의 하드 제약과 정면 충돌**한다:

- `CLAUDE.md`: "법적/이민 콘텐츠 창작 금지, 면책·경고·불확실성 고지 약화 금지."
- `REBRAND_VISABLE_DESIGN.md` §4/§6: "**장식 파티클·과한 그라데이션 금지**, 한 화면 핵심 그래픽 1개, 다크패턴 5종 전면 차단."
- `PARADISO_UX_DIRECTION_LOCK.md` §2: "메인 `<script>` 바이트 보존, `id`·`data-action` 불변, **신규 웹폰트·React/Babel·새 런타임 금지**."

따라서 이 라이브러리를 **"보이는 결과물(HTML/CSS 데코)"로 소비하면 실패**한다.
정답은 라이브러리의 **"작업 방식(capture → analyze → spec → prompt → verify)"을 소비**하는 것이다 —
Meng To가 브랜딩·톤을 토스에서 *자산*이 아닌 *원칙*만 가져오라 한 리브랜드 문서(REBRAND §2)와 **정확히 같은 논리**다.

---

## 2. 선별 매트릭스 — 채택 / 조건부 / 거부

| 스킬군 | 판정 | 이유 | 적용 표면 |
|---|---|---|---|
| `stitched-full-page-capture` (전체 페이지 캡처) | ✅ **채택** | 저장소는 이미 감사 문화가 강함(`docs/audits/*`, `docs/design/*_QA.md`). 3표면 × 2테마(civic_editorial/archive_diary) × 다크/라이트 × 다국어의 **시각 회귀 베이스라인**을 자동화. 픽셀을 바꾸지 않으므로 보존 계약과 무충돌 | 3표면 전부 |
| `html-to-interaction-prompts` (인터랙션 스펙 추출) | ✅ **채택** | 현재 트랜지션이 표면마다 제각각(`0.15s`/`0.18s`/`0.2s`/`0.25s`). 현 마크업에서 인터랙션 스펙을 추출→**모션 토큰 통일**의 입력으로. CSS만 건드리므로 안전 | 3표면 전부 |
| `video-to-superprompt` (영상→프롬프트) | ✅ **채택(비-프로덕션)** | Waymaker 과업 플로우 화면녹화→온보딩/설명 프롬프트. **제품 코드가 아닌 마케팅·문서·데모** 산출물로 한정 | Waymaker(외부 데모) |
| 레이아웃/여백/타이포 리듬 스킬 (`web-design`) | ⚠️ **조건부** | 8pt 그리드·컨테이너 3종·Pretendard 스케일이 이미 캐노니컬(UX Lock §3). 신규 토큰 도입이 아니라 **기존 토큰 정합성 점검**으로만 사용 | Visable·New Home |
| CSS 효과·그라데이션 스킬 | ⚠️ **조건부** | REBRAND §6 기준 통과 시만: 핵심 그래픽 1개, 중간 명도, 라이트/다크 양쪽 가독. New Home 히어로의 기존 `radial-gradient` 워시 정도가 상한선 | New Home 한정 |
| WebGL / 파티클 / 커서 트레일 / 히어로 대형 애니메이션 | ❌ **거부** | REBRAND §6 "장식 파티클 금지" + 성능·다크패턴·`prefers-reduced-motion` 리스크. Visable의 `starCanvas`·스포트라이트는 *기존 보존 대상*이지 확장 대상이 아님 | 없음 |
| 신규 디스플레이 폰트 도입 스킬 | ❌ **거부** | UX Lock §2 "신규 웹폰트 금지." archive_diary용 Unbounded/Pixelify/Space Mono는 *이미 로드된 예외*이며 그 이상 추가 불가 | 없음 |
| `daily-ui-inspiration-capture` | ❌ **거부** | 노션 원문도 "멩투 개인 저장소 전용, 사실상 재현 불가"로 분류 | 없음 |

**규칙:** 위 표에서 ❌인 스킬이 만든 산출물은 리뷰에서 폐기한다(REBRAND 프롬프트의 "위반 시 산출물 폐기" 게이트와 동일).

---

## 3. 표면별 전략

세 표면은 **같은 팔레트, 다른 온도·밀도·장식**(REBRAND §2)이다. 개선도 같은 원칙으로 차등한다.

### 3.1 Visable — 이성·명료 (`index.html`)

**정체:** 비자·체류 정보. `clarity-forward`. near-white 베이스, 높은 위계 대비, 장식 최소.
**현 강점:** 캐노니컬 토큰 고정, 결과 카드 9단계 위계(UX Lock §4), 상태 머신 `landing→searching→searched`, 스포트라이트 히어로.
**제약(절대):** UX Lock §2 보존 계약 — 메인 `<script>` 바이트 보존, `id`/`data-action`/`data-vcode` 불변, Emerald 단일·화면당 ≤3, WCAG는 `primary-deep`+`neutral`.

**개선 기회 → 적용 스킬**

1. **인터랙션 일관성(P0).** `html-to-interaction-prompts`로 검색바(`.sbar`)·결과카드(`.vc`)·모달 5종의 현 인터랙션을 스펙화 → **호버/포커스/전환 타이밍을 하나의 모션 토큰 세트로 수렴**(§4.1). CSS만 수정, 마크업 불변.
2. **검색 결과 카드 밀도(P1).** 내부 design-handoff 노트(`index.html` L42–43)가 이미 `IMPROVE`로 표시: `.sbar`·`.vc`를 `rounded-2xl(16–24px)` 글래스 타일 + 은은한 그림자 + accent 호버로. **스캔 경로(코드→도메인→절차→문서→출처)는 불변**, 표면 질감만 상승.
3. **히어로 게이트웨이 리듬(P2).** `stitched-full-page-capture` 베이스라인으로 히어로 수직 리듬(UX Lock §6)을 캡처→토스식 여백 규율과 대조. 서사 골격(HeroGateway→StatBridge→FeatureTrust)은 유지.

**하지 말 것:** 스포트라이트·`starCanvas` 확장, 데코 그라데이션 추가, 아나그램/브러시 잔존(→ 하우스로), 토스 블루 차용.

### 3.2 New Home — 감성·서정 (`new-home.html`)

**정체:** 국적·귀화. `paradiso-warm` editorial. warm paper 베이스, "You Belong Here", 도착·정착의 감성적 결과.
**현 강점:** `radial-gradient` 히어로 워시(L149–153), archive_diary 키치 테마(오프셋 그림자 `4px 4px 0`), 강한 반응형·접근성(색 비의존 칩, `focus-visible`, `word-break: keep-all`).
**제약:** editorial 장식은 **허용되지만** 여전히 REBRAND §6(핵심 그래픽 1개·중간 명도)와 다크패턴 금지 아래.

**개선 기회 → 적용 스킬**

1. **감성 서사의 시각적 밀도(P1).** New Home은 세 표면 중 **유일하게 데코 여지가 있는 곳**이다. 조건부 CSS 효과 스킬로 히어로·`pathway-steps`(정착 여정)를 *여정(journey)* 은유로 강화 — 단, 그라데이션은 기존 `--cyL`/`--acL` 워시 수준을 상한으로.
2. **스크롤 리빌 모션(P2).** 섹션 진입 시 절제된 페이드/슬라이드. **`@media (prefers-reduced-motion: reduce)` 필수**(이미 L565 존재 — 패턴 재사용). `html-to-interaction-prompts`로 New Home과 Visable의 리빌을 **동일 타이밍 토큰**으로 묶어 하우스 일관성 확보.
3. **키치(archive_diary) 테마 정합성(P2).** `stitched-full-page-capture`로 civic_editorial ↔ archive_diary ↔ 다크 3상태를 나란히 캡처, 오프셋 그림자·네오브루탈 보더의 대비를 감사.

**하지 말 것:** 감성을 이유로 파티클/WebGL 도입, 면책·주의 카피(`.nh-caution`·`.nh-source-disclaimer`)의 공식 톤 약화.

### 3.3 Waymaker — 과업·안내 (`ai.html` + `waymaker-navigator.js/css`)

**정체:** AI 안내 도우미. `visable-dark`. 두 제품 공통 진입. 모바일-퍼스트 스텝 위저드.
**현 강점:** 철저한 모바일 우선(360/390/430 명시), ≥44px 터치 타겟, 안전영역 sticky 액션바, **커버리지 배지가 색만이 아니라 아이콘+텍스트**(`✓`/`◐`/`!`/`—`), reduced-motion 전면 중화.
**제약:** 다크 서피스, 커버리지 신뢰 표기(`CITATION_VERIFICATION_NOT_WIRED` 상태 고려 — 과대주장 금지, UX Lock §8).

**개선 기회 → 적용 스킬**

1. **스텝 전환 마이크로 인터랙션(P1).** 현재 위저드 스텝 전환이 정적. `html-to-interaction-prompts`로 진행바(`.wm-progress-bar`)·스텝 헤딩 포커스 이동을 스펙화 → **방향성 있는 전환**(다음=우슬라이드, 뒤=좌슬라이드)로 "안내받는" 감각 강화. 모두 reduced-motion 존중.
2. **결과 패킷 스캔성(P1).** `.wm-packet` 결과가 정보 밀도 높음. 커버리지 배지·아코디언·문서 체크리스트의 **시각 위계를 캡처로 감사**(`stitched-full-page-capture`) 후 여백·그룹핑 조정. 신뢰 표기 카피는 불변.
3. **온보딩 데모(P2, 비-프로덕션).** `video-to-superprompt`로 "체류자격 검색→절차 선택→서류 패킷" 플로우를 화면녹화→설명 프롬프트→**문서/마케팅용 데모**(Fable 5). 제품 코드에는 미반영.

**하지 말 것:** 다크 배경에 글로우/네온 남발, 커버리지 색상만으로 상태 표현(현 아이콘+텍스트 원칙 훼손), 로딩 스피너 외 장식 애니메이션.

---

## 4. 크로스-커팅 개선 (3표면 공통)

### 4.1 모션 토큰 통일 (가장 큰 단일 레버, P0)

현재 트랜지션 지속시간이 파일·컴포넌트마다 흩어져 있다(`0.1s`/`0.15s`/`0.16s`/`0.18s`/`0.2s`/`0.25s`).
`html-to-interaction-prompts`로 3표면의 인터랙션을 일괄 추출 → **공유 모션 토큰**으로 수렴:

```
--motion-fast:   120ms   /* 호버·포커스·칩 */
--motion-base:   180ms   /* 카드·버튼 트랜스폼 */
--motion-modal:  220ms   /* 모달 진입 scale(0.97→1) */
--ease-out:      cubic-bezier(0.22, 1, 0.36, 1)
```

- **additive**만 허용 — 기존 값 삭제/리네임 금지(REBRAND 프롬프트 §산출 규칙).
- 모든 모션은 `@media (prefers-reduced-motion: reduce)`에서 중화(Waymaker CSS L359 패턴이 레퍼런스).

### 4.2 접근성 정례화

세 표면 모두 이미 우수(색 비의존 라벨, focus-visible, keep-all). AI 스킬로 **회귀 방지**를 자동화:
`stitched-full-page-capture` 결과에 대해 대비비(Emerald+흰텍스트 3.21:1 미달 재발 감시)·터치타겟·포커스 링을 체크리스트화.

### 4.3 성능 가드

- Pretendard 단독 유지. archive_diary 3폰트(Unbounded/Pixelify/Space Mono)는 **키치 테마 활성 시에만** 필요 → 지연 로드 여부 점검(추가 폰트 도입은 금지, 기존 로드 최적화만).
- WebGL/파티클 거부로 메인 스레드 부담 원천 차단.

### 4.4 다크패턴 가드 (불변)

REBRAND §6 5종은 civic 제품에서 절대선. AI가 생성한 어떤 CTA/모달/바텀시트도 이 게이트를 통과해야 채택:
진입 인터럽트 금지 · 뒤로가기 트랩 금지 · 탈출구 상시 · 예상 못한 광고 금지 · **CTA는 결과를 말한다**.

---

## 5. 실행 워크플로우 — AI 스킬을 파이프라인에 넣는 법

노션 글의 "SKILL.md 복사→붙여넣기→요청"을 저장소의 감사·검증 문화에 맞게 정식화한다:

```
① CAPTURE   stitched-full-page-capture
            → 3표면 × {civic_editorial, archive_diary} × {light, dark} × {ko,en,zh} 베이스라인
            → docs/design/ 하위 감사 이미지로 보관
      │
② AUDIT     캡처 vs REBRAND_VISABLE_DESIGN.md / UX_DIRECTION_LOCK.md 대조
            → 개선 지점 = "IMPROVE" 태깅 (index.html L42 handoff 노트 형식 재사용)
      │
③ SPEC      html-to-interaction-prompts
            → 현 인터랙션을 스펙화 → §4.1 모션 토큰 초안
      │
④ PROMPT    REBRAND_CLAUDE_DESIGN_PROMPT.md에 캡처·스펙·개선 태그를 첨부해 실행
            (필요 시 산출 프롬프트를 Fable 5로 프로토타이핑 — 프로덕션 직행 금지)
      │
⑤ IMPLEMENT 표면별 개별 PR. additive CSS·표면 문자열만. 한 번에 한 파일, 작게.
      │
⑥ VERIFY    bash scripts/check_repo.sh (4단계)
            grep 보존 계약 게이트 (react/babel/금칙어 = 빈 결과)
            tests/e2e/*.spec.mjs (new-home / waymaker-navigator)
            → 통과 전 다음 표면 착수 금지
```

**요지:** AI 스킬은 ①③(캡처·스펙)과 ④(프롬프트)에만 투입한다. ⑤⑥(구현·검증)은 기존 보존 계약·CI가 지배한다.

---

## 6. 우선순위 로드맵

| 우선 | 작업 | 스킬 | 표면 | 리스크 |
|---|---|---|---|---|
| **P0** | 시각 회귀 베이스라인 구축 | stitched-full-page-capture | 3표면 | 없음(캡처만) |
| **P0** | 모션 토큰 통일(additive) | html-to-interaction-prompts | 3표면 | 낮음(CSS만) |
| **P1** | Visable 검색바·결과카드 질감 상승 | 조건부 CSS | Visable | 중(보존 계약 준수 필요) |
| **P1** | Waymaker 스텝 전환·패킷 스캔성 | interaction-prompts | Waymaker | 중(신뢰 카피 불변) |
| **P1** | New Home 여정 서사 밀도 | 조건부 CSS/효과 | New Home | 중(§6 명도 기준) |
| **P2** | 스크롤 리빌 모션 | interaction-prompts | Visable·New Home | 중(reduced-motion 필수) |
| **P2** | 온보딩/데모 영상 | video-to-superprompt | Waymaker(외부) | 낮음(비-프로덕션) |

각 P는 **독립 PR**. P0 두 건이 이후 모든 작업의 입력(베이스라인·토큰)이므로 선행.

---

## 7. 완료 기준 / 측정 지표

- **일관성:** 3표면의 트랜지션이 §4.1 토큰 4개로 100% 수렴(grep으로 산발 duration 0건 지향).
- **접근성:** Emerald+흰텍스트 AA 미달 0건, 터치타겟 <44px 0건, 색-only 상태표기 0건.
- **보존:** `scripts/check_repo.sh` 4단계 + 보존 grep 전 PR 통과, `tests/e2e` 그린.
- **절제:** WebGL/파티클/신규폰트 도입 0건(거부 목록 준수).
- **회귀:** stitched 캡처 베이스라인 대비 의도치 않은 시각 변화 0건.

---

## 8. 리스크와 가드레일

| 리스크 | 완화 |
|---|---|
| AI 스킬이 화려한 데코를 유도해 civic 신뢰 톤 훼손 | §2 선별 매트릭스 ❌ 게이트, 산출물 폐기 규칙 |
| `index.html` 단일 파일 보존 계약 위반 | 한 표면 = 한 PR, additive만, `scripts/check_repo.sh` 선통과 |
| 모션 과다 → reduced-motion/성능 저하 | 모든 모션 reduced-motion 중화 의무, WebGL 원천 거부 |
| 면책·출처·불확실성 카피 약화 | 라이팅 하이브리드(REBRAND §5): 돕는 말=해요체, 보호하는 말=공식 톤 불변 |
| Fable 5 프로토타입의 프로덕션 직행 | 워크플로우 ④→⑤ 사이 보존 계약·CI 게이트 필수 |

---

## 9. 결론

Meng To의 75개 스킬은 **"어떻게 빠르게 화려하게 만드나"**를 가르친다.
Visable·New Home·Waymaker에 필요한 건 **"어떻게 일관되고 신뢰감 있게 다듬나"**다.

그래서 이 전략은 라이브러리에서 **캡처·스펙·프롬프트라는 프로세스만 뽑아** 저장소의 감사·보존 문화에 이식하고,
데코 스킬은 명시적으로 거부한다. 세 표면은 성격(이성/감성/과업)에 따라 같은 스킬을 다른 강도로 받되,
셋 다 **하나의 모션·접근성·다크패턴 규율** 아래 수렴한다 — 이것이 리브랜드가 목표한 *House-of-Brands 일관성*의 완성이다.

> **다음 액션:** P0 두 건(캡처 베이스라인 + 모션 토큰 초안)을 착수 승인받는다. 나머지는 그 위에 쌓는다.

*근거 문서: `docs/design/REBRAND_VISABLE_DESIGN.md` · `docs/design/PARADISO_UX_DIRECTION_LOCK.md` · `docs/design/REBRAND_CLAUDE_DESIGN_PROMPT.md` · `CLAUDE.md`*
