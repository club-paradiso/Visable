# Codex Desktop 인수인계 — Waymaker 법률 근거 · 통합 검색 · 취업 신고 분석

작성일 2026-08-03 · 최종 갱신 2026-08-03

이 문서는 "이 컨테이너에서 더 진행할 수 없는 일"만 넘기기 위한 것이다. 코드로
할 수 있었던 작업은 남기지 않고 이미 반영했다. 아래 §1이 그 경계선이고,
§4가 Codex Desktop에 그대로 붙여넣을 수 있는 작업 프롬프트다.

> **머지 완료 (2026-08-03).** 이 문서 초안은 브랜치
> `claude/waymaker-legal-unified-search-bsw1gl` 와 Draft PR
> [#549](https://github.com/lucanomics/Paradiso/pull/549) 를 기준으로 쓰였다.
> **#545 · #548–#555 는 전부 `main` 에 머지됐고 열려 있는 PR 은 없다.**
> 따라서 아래 작업 프롬프트의 기준 브랜치는 **`main`** 이다. 남은 것은 코드가
> 아니라 자격증명·사람 확인·사용자 결정이 필요한 항목뿐이다 (TASK A · C · D · E).

---

## 0. 절대 어기면 안 되는 제약 (모든 후속 작업 공통)

원 스펙에서 그대로 가져온 것이다. Codex에서 이어받을 때도 동일하게 적용한다.

- LLM은 **법령명·조문 번호·판례 번호·비자 코드·직종 코드·업종 코드를 창작할 수 없다.**
- 공개 프런트엔드에 **API 키, OC, 내부 URL, 디버그 정보가 노출되지 않는다.**
- **직종 KSCO8과 업종 KSIC11은 절대 혼합하지 않는다.**
- **검색 실패와 검색 결과 없음은 다른 상태다.**
- AI가 검색이나 공식 근거를 대체하지 않는다. **기본 검색은 AI 장애와 무관하게 항상 작동한다.**
- **승인되지 않은 청크는 AI 직접 근거로 사용하지 않는다.**
- API key와 OC가 **로그·응답·source URL에 없어야 한다.**
- 외부 문서를 **raw `innerHTML`로 렌더링하지 않는다.** 공식 URL allowlist를 유지한다.
- **검증 실패 상태에서 UI가 "실시간 검증 완료"라고 표시하면 안 된다.**
- `visa_data.json` / `backend/data/visas.json` / `doc_master.json` 은 **보호 파일**
  이다. 대량 재작성 금지, 안전한 외과적 수정만 허용 (`CLAUDE.md` 참조).
- **PR을 merge하거나 approve하거나 Ready for review로 바꾸지 않는다.** Draft 유지.

---

## 1. 진행 가능 여부 판정

| 항목 | 여기서 가능? | 근거 |
| --- | --- | --- |
| UX-07 `Legal / Entry` (434:5) — 깊이별 예상 시간, 체류자격 컨텍스트 칩 | ✅ 완료 | 커밋 `8eeb8a2` |
| UX-07 `Legal / Result` (436:8) — 메모 구조 | ✅ 완료 | 커밋 `8eeb8a2` |
| UX-09 (443:4) 인터랙션 규칙 | ✅ **여기서 완료** | 대부분 이미 충족이었고 나머지는 `6cd99d7` |
| UX-10 (445:4) `Spec / Behavior & A11y` | ✅ **여기서 완료** | skip link · `aria-busy` · `word-break` 3건 수정 (`6cd99d7`) |
| UX-10 (445:4) `Spec / Foundations` 토큰 마이그레이션 | ✅ **완료됨** | 초안 작성 시점엔 "사용자 결정 사항"이었으나, 대조해 보니 **PR #551 이 이미 9개 매핑을 전부 적용**했다. 대비 실측 통과 + `check_civic_tokens.mjs` 로 고정 → TASK E |
| 운영 스모크 (Railway `/api/legal/*`, law.go.kr 실호출) | ⛔ 불가 | 이 컨테이너에서 egress 차단. 아래 §2 재확인 결과 참조 |
| 매뉴얼 승인 (`approved` 상태 만들기) | ⛔ 불가 | 코드 작업이 아니라 **사람의 조문 단위 인증**이 필요. 아래 §3 |
| Figma 파일 수정 (`01 Design System` 팔레트, `#177361`→`#0B7357`, 안전 상태 컴포넌트 추가) | ⚠️ 기술적으론 가능, **하지 않음** | 해당 파일은 롤아웃 계획을 가진 다른 세션 소유. 단독 수정 대신 확인 후 진행할 사항 |

> **정정.** 이 문서의 초안은 UX-09 / UX-10 을 "children 0, 빈 프레임"이라고 적었다.
> **틀렸다.** 둘 다 canvas(페이지)이고 내용이 가득 차 있다. UX-09 는 플로우 맵 3개 +
> 인터랙션 규칙 + 프로토타입 연결 현황, UX-10 은 Foundations / Component Contract /
> Behavior & A11y / Theme Coverage 4개 프레임이다. `get_metadata` 를 프레임으로
> 조회했다가 잘못 읽은 것이다. 남은 작업의 크기가 달라지므로 그대로 남겨 둔다.

즉 **Codex 로 넘길 것은 TASK A · C · D · E 네 가지**다 (TASK B 는 완료돼 §4에서 취소선 처리).

### 1b. 남은 4건 — 누가 해야 하는가

에이전트가 "아직 안 한" 것이 아니라, **에이전트가 해서는 안 되거나 할 수 없는** 것들이다.

| 태스크 | 막고 있는 것 | 실행 주체 | 대리 수행 가능? |
| --- | --- | --- | --- |
| **A** 운영 스모크 | 자격증명 + 상류 네트워크 | 키를 가진 환경(Codex Desktop / 로컬) | ✅ 사람이 환경만 주면 에이전트가 실행 가능 |
| **C** 매뉴얼 승인 | 원본 PDF 와 OCR 의 조문 단위 대조 | **사람만** | ❌ 자동화하면 §0 "창작 금지" 위반 |
| **D** Figma 파일 수정 | 파일 소유 세션의 롤아웃 계획 | 사용자 확인 후 누구든 | ⚠️ 소유 확인 먼저 |
| ~~**E** Foundations 토큰 마이그레이션~~ | — | — | ✅ **완료 (PR #551 + `check_civic_tokens.mjs`)** |

**A · D 는 "사람이 문을 열어주면 에이전트가 끝낼 수 있는" 일이고,
C 만이 성질상 끝까지 사람의 일이다.**

---

## 2. 차단 사실 (2026-08-03 재확인)

```
LAW_API_OC=unset   LAW_API_KEY=unset   OPENROUTER_API_KEY=unset   PARADISO_API_BASE=unset
curl https://www.law.go.kr/                                     → 000 (연결 자체가 안 됨)
curl https://web-production-14f9a.up.railway.app/health         → 000
curl https://web-production-14f9a.up.railway.app/api/legal/...  → 000
```

> **정정.** 이 문서 초안은 Railway 호스트를 `paradiso-production.up.railway.app`
> 이라고 적었다. **그런 호스트는 없다.** 저장소가 실제로 쓰는 값은
> `assets/js/unified-search.js` · `assets/js/legal-source-search.js` · `ai.html` ·
> `index.html` 의 `DEFAULT_API_BASE`, 즉 **`web-production-14f9a.up.railway.app`**
> 이다. 둘 다 이 컨테이너에서는 `000` 이라 차단 결론 자체는 바뀌지 않지만,
> 스모크를 도는 쪽이 잘못된 URL 을 두드리면 안 되므로 바로잡는다.

`000`은 HTTP 오류가 아니라 **연결이 성립하지 않았다**는 뜻이다. 그래서 이 브랜치의
법령·판례 경로는 전부 **목/픽스처 기준으로만** 검증되어 있다. 실제 상류 응답
형태가 픽스처와 다를 가능성은 **남아 있고, 이 컨테이너에서는 좁힐 수 없다.**

이 상태에서도 아래는 전부 통과한다 (오프라인 결정론 경로):

```bash
bash scripts/check_repo.sh                        # 전체 저장소 검증
node scripts/check_legal_source_search.mjs        # 313/313
node scripts/check_legal_source_search_dom.mjs    # 68/68 (jsdom 없으면 SKIP)
node scripts/check_unified_search.mjs             # 81/81 (#553 에서 대비 검사 2건 추가)
node scripts/check_employment_code_analyzer.mjs
node scripts/check_i18n_coverage.mjs              # 1236 keys × 14 langs
cd backend && python3 -m pytest tests/ -q
```

브라우저가 필요한 검증 (아래 실행 경로 주의):

```bash
PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium \
  npx playwright test tests/e2e/ux10-a11y.spec.mjs tests/e2e/unified-search.spec.mjs
```

**Playwright 를 돌릴 때는 브라우저 경로를 반드시 넘긴다.** 이 컨테이너에 미리 깔린
Chromium 은 `@playwright/test` 가 기대하는 빌드와 다르다. 그냥 실행하면 전부
"Executable doesn't exist … chromium_headless_shell-1234" 로 죽고, 이게 **테스트
실패처럼 보인다** (실제로 한 번 그렇게 잘못 읽었다). `npx playwright install` 을
실행하지 말고 `playwright.config` 가 이미 지원하는 환경변수를 쓴다:

```bash
PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium \
PARADISO_E2E_PORT=4173 npx playwright test tests/e2e/unified-search.spec.mjs
```

---

## 3. 매뉴얼 승인 상태 (사람이 해야 하는 부분)

`data/manual_approval_index.json` 현재 상태 — **`approved` 0건**:

| 문서 | 상태 |
| --- | --- |
| `visa_manual_2026_06_17_pdf` | `parsed` |
| `stay_manual_2026_06_23_pdf` | `parsed` |
| `stay_manual_2026_06_01_pdf` | `superseded` |
| `stay_manual_2026_05_pdf` | `superseded` |
| `visa_manual_2026_05_pdf` | `superseded` |
| `stay_manual_2026_06_17_txt` | `superseded` |
| `visa_manual_2026_06_17_txt` | `superseded` |
| `hikorea_latest_manual_notice_260623` | `draft` |
| `law_api_placeholder` | `draft` |
| `hikorea_notice_placeholder` | `draft` |
| `moj_immigration_notice_placeholder` | `draft` |

승인 게이트(`backend/services/manual_registry.py` `evidence_gate`)는 **fail-closed**
로 동작하므로, `approved`가 0건이어도 제품은 정상 동작한다 — 다만 **직접 근거로는
아무 청크도 쓰이지 않고**, UI는 "직접 근거 없음"(`no-direct-manual`) 상태를 표시한다.
이건 버그가 아니라 설계된 안전 동작이다.

`approved`로 올리려면 **OCR 텍스트와 원본 PDF를 조문 단위로 대조한 사람의 확인**이
필요하다. 자동화하면 §0의 첫 번째 제약("창작 금지")과 CLAUDE.md의 "OCR 결과를 확인된
요건으로 취급하지 말 것"을 정면으로 위반한다. **에이전트가 대신 승인하면 안 된다.**

---

## 4. Codex Desktop 작업 프롬프트

각 블록을 그대로 붙여넣으면 된다. 앞에 §0을 함께 붙이는 것을 권장한다.

### TASK A — 운영 환경 스모크 (자격증명 필요)

```
저장소: lucanomics/Paradiso · 기준 브랜치 main (관련 PR 은 전부 머지됨)

목표: 법령/판례/리서치 경로를 실제 상류 서비스에 대고 처음으로 검증한다.
지금까지는 목·픽스처로만 검증되어 있다. 코드는 이미 main 에 있으므로 이 태스크의
산출물은 "검증 결과"이고, 불일치가 발견되면 그때 새 브랜치를 파서 고친다.

필요한 환경변수 (없으면 여기서 중단하고 보고할 것. 임의로 우회하지 말 것):
  LAW_API_OC          법제처 오픈 API OC
  LAW_API_KEY         법제처 API 키
  OPENROUTER_API_KEY  AI 합성용 (없으면 deterministic 경로만 검증)

실행:
1) LAW_API_OC=... python3 scripts/smoke_legal_api.py
   - 종료 코드 0 = 전 쿼리가 결과 또는 정상적인 "결과 없음"에 도달
   - 종료 코드 1 = 전송/파싱 오류. 이때 실패한 쿼리와 원인을 그대로 보고
2) 백엔드를 로컬 기동한 뒤:
   curl -s -X POST localhost:8000/api/legal/research \
     -H 'Content-Type: application/json' \
     -d '{"question":"D-10에서 시간제 취업이 가능한가요?","locale":"ko","depth":"basic"}' | jq .
   curl -sN -X POST localhost:8000/api/legal/research/stream \
     -H 'Content-Type: application/json' -H 'Accept: text/event-stream' \
     -d '{"question":"E-7 전공 일치 판단 기준","locale":"ko","depth":"pro"}'
   - stream은 start → step×6 → done 순으로 와야 한다. 순서가 다르면 그대로 보고
3) Railway 배포본에도 같은 두 호출을 실행
   호스트는 https://web-production-14f9a.up.railway.app 이다
   (저장소의 DEFAULT_API_BASE 값. 다른 이름을 쓰지 말 것)
   main 이 머지돼 있으므로 이 배포본에는 이미 새 경로가 올라가 있어야 한다.
   /api/legal/research/stream 이 404 면 배포가 안 된 것이므로 그것부터 보고

확인해야 할 것 (실패 시 코드를 고치는 것이 이 태스크의 산출물):
- 응답 본문·로그·source URL 어디에도 OC와 API 키가 나타나지 않는다 (검색해서 확인)
- 검색 실패와 결과 없음이 서로 다른 상태로 내려온다 (같은 상태로 뭉개지면 버그)
- 상류가 500/타임아웃일 때 기본 검색이 여전히 동작한다
- 실제 응답 스키마가 backend/services/legal_research.py 의 가정과 일치한다.
  다르면 파서를 고치고, 무엇이 달랐는지 커밋 메시지에 기록한다

금지: PR merge / approve / Ready for review 전환. Draft 유지.
```

### ~~TASK B — UX-09 인터랙션 규칙 · UX-10 Behavior & A11y 감사~~ → **완료됨 (`6cd99d7`)**

Codex 로 넘기지 않는다. 감사와 수정을 모두 끝냈다.

이미 충족하고 있던 것: focus-visible 2px 링 + offset 2 · 자동완성 ↑↓/Enter/Esc ·
에러마다 다음 행동 1개 이상(legal 은 `FAILURE_STATES` 7종) · `aria-live="polite"`
결과 안내 · 리서치 진행 블록 `aria-busy` · 진행 단계 `aria-current="step"`.

미충족 3건을 고쳤다:

1. **skip link** — `<body>` 첫 요소로 `#mainContent` 를 가리키게 추가. `display:none`
   이 아니라 화면 밖에 두었다 — 숨긴 요소는 포커스를 못 받고, 포커스를 못 받는
   skip link 는 skip link 가 아니다. 14개 언어 팩 전부에 문자열 추가.
2. **통합 검색 레이어 `aria-busy`** — `setSearchBarState` 한 곳에서 구동해 보이는
   상태와 알리는 상태가 어긋날 수 없게 했다.
3. **`word-break`** — 이 문서 초안이 "index.html 에 1곳뿐"이라고 적었던 건 **틀렸다.**
   콜론 뒤 공백을 놓친 grep 이었고 실제로는 163곳에 적용돼 있다. 진짜 누락은 더
   좁았고 이 PR 이 만든 것이었다 — `.us-*` 규칙만 예외였다. prose 선택자에 한정한
   규칙 하나로 처리하되 `overflow-wrap: anywhere` 를 함께 뒀다. `keep-all` 만 쓰면
   끊을 곳 없는 라틴 문자열(law.go.kr URL 등)이 카드를 넘쳐 흐른다.

브라우저 테스트가 값을 했다: **첫 검색에서 `aria-busy` 가 전혀 설정되지 않는 것**을
잡아냈다. 레이어 엘리먼트는 첫 렌더에서 지연 생성되는데 그 렌더는 요청이 끝난
**뒤에** 일어나므로, `getElementById` 조회는 대기가 가장 긴 바로 그 순간에 조용히
아무 일도 하지 않았다. `ensureMount()` 로 바꿨다.

검증: `tests/e2e/ux10-a11y.spec.mjs` 3건(실제 탭 순서 · 진행 중 busy · 실패 경로에서
busy 해제) + `check_unified_search.mjs` 정적 검사(76 → 79, 이후 #553 에서 → 81).

### ~~TASK E — UX-10 `Spec / Foundations` 토큰 마이그레이션~~ → **완료됨 (PR #551)**

> **2026-08-03 확인.** 사용자 승인을 받아 착수하려다 대조해 보니 **이미 반영돼
> 있었다.** PR #551 이 `:root:not([data-theme="archive_diary"])` 에 civic 토큰
> 레이어를 만들면서 제안된 9개 매핑을 전부 적용했다 — `--bg0 #F7F4EF` ·
> `--bg1 #FFFCF5` · `--bd #E6E6EE` · `--t1 #1C1F29` · `--t2 #4D5261` ·
> `--ac #177366` · `--cWk #F2C879` · `--cy #D95C47`, 그리고 주 CTA 용 신설
> 변수 `--cta #0B4F44`. `archive_diary` 는 스코프 선택자의 `:not()` 로 분리돼
> 있다.
>
> 아래 "진행할 때 반드시 지킬 것" 은 실측으로 확인했고 **전부 통과**한다
> (라이트/다크 양쪽): 본문 14.98/12.30, 보조 7.10/7.69, 액센트 5.57/8.72,
> 주 CTA 흰 글자 9.48 (AAA 7:1 기준). `--cWk`(원색 1.54:1)와 `--cy` 는 **텍스트
> 색으로 쓰이지 않고**, 읽히는 것은 `--t1` 쪽으로 섞은 파생 잉크
> (`--color-warning` 6.07:1 · `--color-error` 6.57:1) 다.
>
> **남아 있던 진짜 문제는 이 기준들이 산문에만 있었다는 것**이다 — #551 이 회귀를
> 낸 조건과 동일하다. `scripts/check_civic_tokens.mjs` (7건) 를 추가해
> `check_repo.sh` 에 연결했고, 팔레트를 "의도적으로" 바꾸면서 상수까지 같이
> 고치는 경우에도 실측 비율이 단독으로 잡는 것을 변이 테스트로 확인했다.
>
> 아래 원문은 무엇을 요구했는지 확인할 수 있도록 그대로 둔다.

<details><summary>원래 TASK E 프롬프트 (완료됨)</summary>

```
저장소: lucanomics/Paradiso
Figma 노드: 445:5 (UX-10 › Spec / Foundations)

배경: 이 프레임은 Figma 토큰 → 이 저장소의 CSS 커스텀 프로퍼티 매핑 표를 담고 있고,
표에 적힌 "현재 라이브" 값이 index.html 실제 값과 정확히 일치한다. 즉 추측이 아니라
코드를 보고 쓴 표다. 프레임 스스로 "Figma 값은 제안이다" 라고 밝히고 있다.

제안된 변경 (그대로 옮김):
  PAPER #F7F4EF      → --bg0   (현재 #F4EFE4 / #062A22)   페이지 배경 교체
  CARD_LIGHT #FFFCF5 → --bg1   (현재 #FFFCF5 / #0C3A30)   라이트 일치 · 다크만 #0D3129
  LINE #E6E6EE       → --bd    (현재 #998058 / #2D5A50)   라이트 보더가 갈색 — 교체
  DARK #1C1F29       → --t1    (현재 #073B32 / #F4EFE4)   본문 색 교체
  GREY #4D5261       → --t2    (현재 #3A544C / #C7BFA8)   보조 텍스트 교체
  EMERALD_TXT #177366→ --ac    (현재 #0B7357 / #3BE4B8)   라이트 미세 조정
  EMERALD_DEEP #0B4F44 → 신설   대응 변수 없음 — 주 CTA 배경용 변수 신설, 하드코딩 금지
  AMBER #F2C879      → --cWk   (현재 #E68A3A)             경고 톤 교체
  CORAL #D95C47      → --cy    (현재 #FF6B5B / #FF8B7A)   오류 톤 교체
  8pt 스케일          → --sp-1..8                          이미 일치, 손대지 않음

왜 이 PR 에서 하지 않았는가: --bg0 / --bd / --t1 / --t2 / --cWk / --cy 는 모든 화면과
양쪽 테마가 읽는 변수다. 이 PR 의 범위(법률 근거 계층 · 통합 검색 · 취업 신고)를
훨씬 넘어서는 사이트 전체 외형 변경이고, 잔여 작업이 아니라 제품 결정이다.

진행하기 전에:
1) 사용자에게 "사이트 전체 팔레트를 바꾸는 변경"임을 명시하고 승인을 받는다.
2) 별도 브랜치·별도 PR 로 낸다. 이 PR 에 섞지 않는다.

진행할 때 반드시 지킬 것:
- 대비 재계산: 본문 WCAG AA 4.5:1 이상, 주 CTA(EMERALD_DEEP + 흰 텍스트) AAA 7:1.
  --ac 를 #177366 으로 옮기면 .us-layer 파생 틴트(color-mix 8%/6% 라이트,
  16%/12% 다크)의 accent-on-soft 여유(현재 ≥5:1)를 다시 재어야 한다.
- 대체 테마(data-theme="archive_diary" 등)는 별도 팔레트다. 함께 끌고 가지 않는다.
- 주 CTA 배경은 새 변수로만 쓴다. 하드코딩된 #0B4F44 를 남기지 않는다.
- 라이트/다크 양쪽 스크린샷으로 회귀를 확인한다.
```

</details>

### TASK C-0 — "하이코리아에서 최신 매뉴얼을 받아 반영" 은 지금 3중으로 막혀 있다

2026-08-03 에 실제로 시도하고 확인한 결과다. 추정이 아니다.

| 경로 | 결과 | 확인 방법 |
| --- | --- | --- |
| 이 컨테이너에서 직접 fetch | ⛔ `000` | `curl https://www.hikorea.go.kr/` — 연결 미성립. `immigration.go.kr` 도 동일 |
| `hikorea-manual-sync` 워크플로 디스패치 | ⛔ `403` | `Resource not accessible by integration` — 통합 앱에 workflow dispatch 권한이 없다 |
| 워크플로가 스스로 다운로드 | ⛔ 대상 없음 | `data/sources/hikorea_manual_sync.json` 의 `download_url` 이 **두 매뉴얼 모두 `null`**. `allow_network: true` 를 켜도 받을 URL 자체가 없다 |

**그리고 게시판 모니터를 "새 매뉴얼 없음"의 근거로 쓰면 안 된다.**
`data/sources/hikorea_manual_board_watch.json` 의 두 타깃 모두
`baseline_content_hash` 가 **`null`** 이다. 파일 자신의 주석이 밝히듯 *"A null
baseline means 'not yet established' — the first run records the current
fingerprint in its report but does not raise a change."* 즉 08-03 실행에서
`Open or update tracking issue on change` 단계가 `skipped` 된 것은 **비교할
기준선이 없었다**는 뜻이지, 게시판이 그대로였다는 뜻이 아니다.
(이 세션에서 실제로 그렇게 오독할 뻔했다.)

**그러므로 실제 경로는 하나뿐이다 — 사람이 파일을 가져온다.**
`hikorea-manual-sync` 워크플로는 이미 그 입력을 갖고 있다:

```
workflow_dispatch inputs:
  manual_hwp_visa   체크아웃 안의 사증 매뉴얼 HWP 경로
  manual_hwp_stay   체크아웃 안의 체류 매뉴얼 HWP 경로
```

즉 최신 HWP 를 저장소에 올리고 그 경로를 넘겨 워크플로를 돌리면, 워크플로가
추출 + **Draft PR 생성**까지 한다. 워크플로 자신이 "never edits production data
— promotion of any legal content is a reviewed, manual step" 라고 명시한다.
자동화가 승인까지 하지 않는다는 §0 제약과 이미 일치하는 설계다.

> **덧붙여 확인할 것 (드리프트 의심).** `hikorea_manual_sync.json` 의
> `hwp_path` 는 아직 `2026_05_21`(사증) / `2026_06_01`(체류) 를 가리키는데,
> `data/manual_approval_index.json` 의 최신 `parsed` 판은
> `2026_06_17`(사증) / `2026_06_23`(체류) 다. 전자는 HWP 원본, 후자는 PDF 판을
> 추적하므로 설계상 다를 수 있으나, **같은 것을 가리켜야 하는데 어긋난 것인지
> 확인이 필요하다.** 확인 없이 어느 쪽도 손대지 않았다.

---

### TASK C — 매뉴얼 승인 (사람 확인 필수, 에이전트 단독 수행 금지)

```
저장소: lucanomics/Paradiso

배경: data/manual_approval_index.json 에 approved 문서가 0건이다. 승인 게이트가
fail-closed 이므로 제품은 정상 동작하지만, 매뉴얼 청크가 직접 근거로 쓰이지 않고
UI는 "직접 근거 없음"을 표시한다.

에이전트가 해도 되는 일:
- 승인 후보 문서의 OCR 텍스트와 원본 PDF의 해당 페이지를 나란히 제시한다
- 불일치·누락·OCR 깨짐 후보를 목록으로 정리한다
- 사람이 확정한 결과를 manual_approval_index.json 에 반영한다 (상태 전이만)

에이전트가 하면 안 되는 일:
- 사람 확인 없이 approval_state 를 approved 로 올리는 것
- OCR 텍스트를 근거로 요건을 새로 쓰거나 보완하는 것
- 확인되지 않은 항목을 "확인됨"으로 표시하는 것

상태 전이는 backend/services/manual_registry.py 의 상태 기계를 따른다.
변경 후 반드시: cd backend && python3 -m pytest tests/ -q && bash scripts/check_repo.sh
```

### TASK D — Figma 측 정리 (소유 세션 확인 후)

> **2026-08-03 재확인 — 아래 항목 2는 폐기하고, 새 항목 0을 먼저 한다.**
>
> **항목 2 폐기.** "UX-0x 의 `#177361` 을 `#0B7357` 로 통일한다"는 지시는 #551
> 이전에 쓰였다. 지금 코드의 `--ac` 는 **`#177366`** 이고, Figma `Spec /
> Foundations`(445:5)의 EMERALD_TXT 도 이미 **`#177366`** 이다. 즉 둘은 이미
> 일치하며, 지시대로 `#0B7357` 로 맞추면 **코드를 되돌리는 셈**이 된다.
> 그 값은 더 이상 저장소에 없다.
>
> **새 항목 0 (우선) — Foundations 매핑표가 거짓이 됐다.** 445:5 하단
> `코드 토큰 매핑` 표의 "현재 라이브" 열은 전부 #551 이전 값이고, "조치" 열은
> 여전히 "교체"라고 적혀 있다. 실제로는 8개 행이 **모두 이미 반영됐다**:
>
> | 행 | 표가 적은 "현재 라이브" | 실제 라이브 |
> | --- | --- | --- |
> | `477:16` --bg0 | `#F4EFE4 / #062A22` | `#F7F4EF` |
> | `477:21` --bg1 | `#FFFCF5 / #0C3A30` | 라이트 일치 · 다크 `#0D3129` 반영됨 |
> | `477:26` --bd | `#998058 / #2D5A50` | `#E6E6EE` |
> | `477:31` --t1 | `#073B32 / #F4EFE4` | `#1C1F29` |
> | `477:36` --t2 | `#3A544C / #C7BFA8` | `#4D5261` |
> | `477:41` --ac | `#0B7357 / #3BE4B8` | `#177366` |
> | `477:46` EMERALD_DEEP | `대응 변수 없음` | `--cta: #0B4F44` 신설됨 |
> | `477:51` --cWk | `#E68A3A / 동일` | `#F2C879` |
> | `477:56` --cy | `#FF6B5B / #FF8B7A` | `#D95C47` |
>
> 경고 프레임 `477:5` 의 "위 컬러 토큰은 현재 라이브 index.html 값과 다르다"
> 도 이제 **사실이 아니다.** 이 상태로 두면 보드를 읽는 사람이 마이그레이션이
> 아직 남았다고 오해한다 — 실제로 이 세션에서 그렇게 오해해 착수했다가
> 대조 끝에 되돌렸다.
>
> → "현재 라이브" 열을 실제 값으로, "조치" 열을 `반영 완료 (PR #551)` 로,
> `477:5` 경고를 "이 표는 반영이 끝났다"는 취지로 바꾼다. 대비 기준은
> `scripts/check_civic_tokens.mjs` 가 지키고 있으므로 보드에서 참조만 걸면 된다.
>
> 항목 1(디자인 시스템 페이지 indigo → emerald)과 항목 3(안전 상태 컴포넌트)은
> 그대로 유효하다. 다만 항목 1 본문의 `--ac: #0B7357` 은 `#177366` 으로 읽는다.

```
Figma 파일 키: pInhK8Oyg04lpL4PMSCB4l

이 파일은 롤아웃 계획을 가진 다른 세션이 소유하고 있다. 단독으로 고치지 말고
소유자에게 확인부터 받는다. 확인이 끝난 뒤에만 아래를 수행한다.

확인 후 할 일:
1) `01 Design System` 페이지의 팔레트가 indigo #2f3e8f 로 남아 있다. UX-0x 페이지는
   emerald 계열이고, 코드의 기본 액센트도 이미 emerald(--ac: #0B7357)다.
   → 디자인 시스템 페이지를 emerald 로 맞춘다. (코드는 이미 맞다. 마이그레이션할
     코드가 남아 있다는 뜻이 아니다.)
2) UX-0x 의 #177361 을 #0B7357 로 통일한다. 두 값은 눈으로 같은 색이고, 사이트
   값이 대비에서 근소하게 낫다 (--us-surface 위 5.69 vs 5.60, 다크 9.46 vs 9.04).
3) 코드에만 있고 디자인에 없는 안전 상태를 컴포넌트로 추가한다:
   forbidden(403/OC 거부), repealed, ambiguous, parse_failed, 미인식 코드 경고,
   manual_card. 각각 §3.6 의 네 스케일(approval / lifecycle / lookup / relevance)
   중 자기 스케일 안에서 서로 다른 형태를 갖는다 — 하나의 색 램프로 합치지 않는다.

use_figma 를 쓰기 전에 반드시 figma-use 스킬을 먼저 로드한다.
```

---

## 5. 지금까지 브랜치에 들어간 것 (요약)

- **UX-03 통합 검색**: 제안 행 7종 + 무타입(`query`, 칩 없음), 해석 스트립, AI 개요,
  결과 상태 카드, 부모/서브코드 스코프 안내, 검색 입력 상태(`loading`/`results`/`error`)
- **UX-07 리걸 리서치**: 6단계 진행 표시 + SSE 스트림(`/api/legal/research/stream`),
  실패 상태 7종(각각 다음 행동 제공), 깊이별 예상 시간, 체류자격 컨텍스트 칩,
  결과 메모 구조(질문 에코 / 확인된·부족한 사실 2열 / 번호 쟁점 / 판례 유추 고지 /
  근거 집계 / 질문 복사)
- **UX-08 취업 신고**: 특수 상태 10종 도출 + 렌더 + 각 상태의 행동, 신고대상≠취업가능
  경고
- **근거 배지**: §3.6 네 스케일을 네임스페이스로 분리 (`approval` / `lifecycle` /
  `lookup` / `relevance`) — 하나의 램프로 합치던 이전 구현을 되돌린 것
- **팔레트**: `.us-layer` 가 자체 emerald 를 버리고 `--ac` 를 별칭으로 사용. 파생
  틴트는 `color-mix` **7%/5%(라이트)**, 16%/12%(다크) — 대비 ≥5:1 유지.
  라이트 값은 원래 8%/6% 였는데, #551 이 `--ac` 를 옮기면서 별칭인 `.us-layer` 도
  같이 끌려가 accent-on-soft 가 4.98:1 로 떨어졌다. #553 에서 틴트를 낮춰 복구하고,
  **임계값 자체를 `check_unified_search.mjs` 의 계산식 검사 2건으로 고정했다** —
  기준이 산문에만 있어서 모든 가드가 초록인 채로 회귀가 나갔던 게 원인이었다

### 알려진 미해결 이슈 (정직한 기록)

- `tests/e2e/new-home.spec.mjs` 는 **`main` 기준으로도 10건이 실패한다** (별도
  worktree 에 원본 `origin/main` 을 체크아웃해 동일 실패를 확인함). 이 브랜치가
  만든 회귀가 아니다.
- ~~`new-home.spec.mjs:63` 이 부하 상황에서 flake 일 수 있다~~ → **해소됨.**
  그 테스트는 `test.skip(viewport.width < 1000)` 을 갖고 있어 `desktop-1280`
  에서만 실행되고 나머지 4개 프로젝트에서는 원래 skip 된다. 올바른 브라우저로
  전체 실행하면 **10 failed (`:8`·`:41` × 5) · 1 passed (`:63`) · 4 skipped** 로
  나온다 — 즉 `:63` 은 통과하고, 실패는 알려진 기존 10건과 정확히 일치한다.
  이전에 "부하성 flake로 추정"이라고 적은 건 브라우저 실행 실패를 테스트 실패로
  잘못 읽은 것이다.
- 상류 실호출 검증은 §2 때문에 **전무하다.** TASK A 가 이걸 다룬다.
