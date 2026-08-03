# Codex Desktop 인수인계 — Waymaker 법률 근거 · 통합 검색 · 취업 신고 분석

작성일 2026-08-03 · 브랜치 `claude/waymaker-legal-unified-search-bsw1gl` · PR
[#549](https://github.com/lucanomics/Paradiso/pull/549) (**Draft 유지**)

이 문서는 "이 컨테이너에서 더 진행할 수 없는 일"만 넘기기 위한 것이다. 코드로
할 수 있었던 작업은 남기지 않고 브랜치에 이미 반영했다. 아래 §1이 그 경계선이고,
§4가 Codex Desktop에 그대로 붙여넣을 수 있는 작업 프롬프트다.

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
| UX-09 (443:4) 인터랙션 규칙 | ⚠️ 부분 가능 | 대부분 이미 충족. 남은 건 감사(audit) 성격 → TASK B |
| UX-10 (445:4) `Spec / Behavior & A11y` | ⚠️ 부분 가능 | skip link · `aria-busy` 등 일부 미충족 → TASK B |
| UX-10 (445:4) `Spec / Foundations` 토큰 마이그레이션 | ⛔ 하지 않음 | **전 화면·양 테마에 영향.** 사용자 결정 사항이지 잔여 작업이 아님 → TASK E |
| 운영 스모크 (Railway `/api/legal/*`, law.go.kr 실호출) | ⛔ 불가 | 이 컨테이너에서 egress 차단. 아래 §2 재확인 결과 참조 |
| 매뉴얼 승인 (`approved` 상태 만들기) | ⛔ 불가 | 코드 작업이 아니라 **사람의 조문 단위 인증**이 필요. 아래 §3 |
| Figma 파일 수정 (`01 Design System` 팔레트, `#177361`→`#0B7357`, 안전 상태 컴포넌트 추가) | ⚠️ 기술적으론 가능, **하지 않음** | 해당 파일은 롤아웃 계획을 가진 다른 세션 소유. 단독 수정 대신 확인 후 진행할 사항 |

> **정정.** 이 문서의 초안은 UX-09 / UX-10 을 "children 0, 빈 프레임"이라고 적었다.
> **틀렸다.** 둘 다 canvas(페이지)이고 내용이 가득 차 있다. UX-09 는 플로우 맵 3개 +
> 인터랙션 규칙 + 프로토타입 연결 현황, UX-10 은 Foundations / Component Contract /
> Behavior & A11y / Theme Coverage 4개 프레임이다. `get_metadata` 를 프레임으로
> 조회했다가 잘못 읽은 것이다. 남은 작업의 크기가 달라지므로 그대로 남겨 둔다.

즉 **"안 된다"에 해당하는 건 아래 다섯 가지**이고, §4의 프롬프트가 이를 다룬다.

---

## 2. 차단 사실 (2026-08-03 재확인)

```
LAW_API_OC=unset   LAW_API_KEY=unset   OPENROUTER_API_KEY=unset   PARADISO_API_BASE=unset
curl https://www.law.go.kr/                                → 000 (연결 자체가 안 됨)
curl https://paradiso-production.up.railway.app/health      → 000
```

`000`은 HTTP 오류가 아니라 **연결이 성립하지 않았다**는 뜻이다. 그래서 이 브랜치의
법령·판례 경로는 전부 **목/픽스처 기준으로만** 검증되어 있다. 실제 상류 응답
형태가 픽스처와 다를 가능성은 **남아 있고, 이 컨테이너에서는 좁힐 수 없다.**

이 상태에서도 아래는 전부 통과한다 (오프라인 결정론 경로):

```bash
bash scripts/check_repo.sh                        # 전체 저장소 검증
node scripts/check_legal_source_search.mjs        # 313/313
node scripts/check_legal_source_search_dom.mjs    # 68/68 (jsdom 없으면 SKIP)
node scripts/check_unified_search.mjs             # 76/76
node scripts/check_employment_code_analyzer.mjs
node scripts/check_i18n_coverage.mjs              # 1235 keys × 14 langs
cd backend && python3 -m pytest tests/ -q
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
저장소: lucanomics/Paradiso · 브랜치 claude/waymaker-legal-unified-search-bsw1gl

목표: 이 브랜치의 법령/판례/리서치 경로를 실제 상류 서비스에 대고 처음으로 검증한다.
지금까지는 목·픽스처로만 검증되어 있다.

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

확인해야 할 것 (실패 시 코드를 고치는 것이 이 태스크의 산출물):
- 응답 본문·로그·source URL 어디에도 OC와 API 키가 나타나지 않는다 (검색해서 확인)
- 검색 실패와 결과 없음이 서로 다른 상태로 내려온다 (같은 상태로 뭉개지면 버그)
- 상류가 500/타임아웃일 때 기본 검색이 여전히 동작한다
- 실제 응답 스키마가 backend/services/legal_research.py 의 가정과 일치한다.
  다르면 파서를 고치고, 무엇이 달랐는지 커밋 메시지에 기록한다

금지: PR merge / approve / Ready for review 전환. Draft 유지.
```

### TASK B — UX-09 인터랙션 규칙 · UX-10 Behavior & A11y 감사

```
저장소: lucanomics/Paradiso · 브랜치 claude/waymaker-legal-unified-search-bsw1gl
Figma 파일 키: pInhK8Oyg04lpL4PMSCB4l
대상 노드: 443:114 (Interaction Rules), 447:4 (Spec / Behavior & A11y)

이건 새 화면을 만드는 작업이 아니다. 두 스펙 프레임이 규칙을 나열하고 있고,
그 규칙이 실제 코드에서 지켜지는지 확인해 미충족분만 채우는 감사 작업이다.

주의: nodeId 없이 get_metadata 를 호출하면 이 파일은 stale 한 2페이지 뷰를 준다.
반드시 nodeId 를 지정하거나 use_figma 로 figma.root.children 을 읽는다.

이미 확인된 것 (재확인만 하면 됨):
- focus-visible 2px 링 + offset 2 → 충족
- 자동완성 ↑↓ / Enter / Esc → 충족
- 에러마다 다음 행동 1개 이상 → 충족 (legal 은 FAILURE_STATES 7종)
- aria-live="polite" 결과 개수 안내 → index.html 에 28곳
- 진행 단계 aria-current="step" → 충족 (스트림이 살아있는 동안만)
- 리서치 진행 블록 aria-busy="true" → 충족

미충족으로 확인된 것 (이게 실제 작업분):
- "본문으로 건너뛰기" skip link 가 없다 (첫 Tab 에 와야 한다).
  index.html 에 넣을 경우 14개 언어 팩 전부에 문자열을 추가해야 한다.
- 통합 검색 레이어에 aria-busy 가 없다. #searchForm 은 이미
  data-us-search-state 를 갖고 있으므로 loading 상태와 함께 aria-busy 를 토글한다.
- word-break: keep-all 이 index.html 에 1곳뿐이다. UX-10 은 긴 한국어 전반에
  적용하라고 한다 — 카드 본문·상태 문구 등 실제로 깨지는 곳을 찾아 적용한다.

각 항목마다:
- 고친 뒤 scripts/check_*.mjs 에 대응 검증을 추가한다 (규칙만 문서에 적지 않는다)
- 라이트/다크 양쪽에서 확인한다
```

### TASK E — UX-10 `Spec / Foundations` 토큰 마이그레이션 (사용자 승인 필요)

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
<!-- TASK E 는 TASK B 바로 뒤에 있다 (토큰 마이그레이션). -->


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
  틴트는 `color-mix` 8%/6%(라이트), 16%/12%(다크) — 대비 ≥5:1 유지

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
