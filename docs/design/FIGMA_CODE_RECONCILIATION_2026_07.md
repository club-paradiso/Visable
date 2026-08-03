# Figma ↔ 코드 계약 대조 기록 (2026-07)

**대상 Figma 파일:** `pInhK8Oyg04lpL4PMSCB4l`
**기준 문서:** `docs/design/UNIFIED_SEARCH_AND_LEGAL_RESEARCH_CONTRACT.md` (PR #545)
**대조 대상 페이지:** `UX-03 Component Library`, `UX-10 Design Specification & Handoff`

PR #545 가 통합검색·법률 근거·취업신고의 **기능 구현**과 함께 설계 계약 문서를 들여왔다.
그런데 Figma UX Workspace 는 그 계약 문서를 읽기 전에 만들어져서, **같은 것을 다른 이름으로
부르고 있었다.** 이 문서는 그 차이를 좁힌 기록이다.

> 이 작업은 렌더링·데이터 위생 작업이다. 법령 내용을 새로 판단하거나 요건을 추가하지 않았다.

---

## 1. 이름을 계약에 맞춘 것

| 이전 (Figma) | 이후 (계약 §3 / §10) | 비고 |
|---|---|---|
| `Search / Unified` | `Search / Unified Input` | `State=Focus` → `State=Focused` 도 함께 정정 |
| `Search / Interpretation` | `Search / Interpretation Strip` | |
| `AI Overview` | `Search / AI Overview` | |
| `Result / Organic Card` | `Result / Status Card` | `Type` 축은 데이터 계약 §4 의 `kind` 열거값을 따른다 |
| `Source / Evidence Card` | `Evidence / Source Card` | |
| `Status / Confidence` | `Evidence / Confidence Badge` | |
| `Status / Evidence` | `Evidence / Relevance Badge` | 계약에 없는 확장. 이름만 계열에 맞췄다 |

---

## 2. 계약에 있는데 Figma 에 없어서 새로 만든 것

### 2.1 근거 배지 4개 척도 (계약 §3.6)

계약은 **"네 개의 서로 다른 척도이며 하나의 색 램프를 공유해서는 안 된다"** 고 못박는다.
기존 Figma 는 이 넷을 `Source Card` 의 `State` 축 하나에 뭉쳐 두고 있었다.
네 개를 시각적으로 다른 형태로 분리했다.

| 컴포넌트 | 값 | 형태 | 코드 |
|---|---|---|---|
| `Evidence / Confidence Badge` | High · Medium · Low | 채운 필 + 점 | `unified_search.classify_intent` → `confidence` |
| `Evidence / Approval Badge` | Approved · NeedsReview · Superseded | 테두리 태그 | `manual_registry.evidence_gate` |
| `Evidence / Law Lifecycle Badge` | Verified · Repealed · Scheduled · Ambiguous | 좌측 색 규칙(rule) | `law_query_normalizer.classify_law_lifecycle` |
| `Evidence / Lookup Failure Badge` | Unavailable · Forbidden · Timeout · ParseFailed · NotFound | 중립 점선 | `law_query_normalizer.evidence_status_for` |

`NotFound`("확인했고 자료가 없다")만 **실선**으로 처리했다.
나머지 넷("확인 자체를 못했다")은 점선이다. 계약이 요구한 "서로 다른 주장, 서로 다른 처리"다.
조회 실패 척도는 전부 중립색이다 — 조회 실패는 품질 판단이 아니기 때문이다.

### 2.2 `Search / Intent Pill` (계약 §3.2)

`classify_intent` 의 8개 분기를 그대로 옮긴 필을 새로 만들었다.

| Figma | 백엔드 상수 |
|---|---|
| ExactCode | `INTENT_EXACT_VISA_CODE` = `exact_visa_code` |
| Keyword | `INTENT_VISA_KEYWORD` = `visa_keyword` |
| Situation | `INTENT_VISA_SITUATION` = `visa_situation` |
| Procedure | `INTENT_PROCEDURE_QUESTION` = `procedure_question` |
| Legal | `INTENT_LEGAL_QUESTION` = `legal_question` |
| Employment | `INTENT_EMPLOYMENT_REPORTING` = `employment_reporting` |
| Feature | `INTENT_FEATURE_NAVIGATION` = `feature_navigation` |
| Unknown | `INTENT_UNKNOWN` = `unknown` |

**계약과 다르게 간 부분:** 계약 §3.2 는 `Intent` 를 Interpretation Strip 의 **변형 축**으로 적었다.
그대로 하면 8 intents × unknown-code × 2 themes = 32개의 거의 동일한 315px 카드가 된다.
시각적 차이가 필 하나에만 있으므로, 의도는 **중첩 컴포넌트 인스턴스**로 모델링했다.
표현력은 같고 유지보수 비용만 줄어든다.

### 2.3 `Search / Interpretation Strip` — `State=UnknownCode` (계약 §3.2)

사용자가 코드 모양이지만 `visa_data.json` 에 없는 토큰(`D-2-99`, `Z-9`)을 입력한 상태다.
계약이 "엣지 케이스가 아니라 실제 상태"라고 명시한 것인데 Figma 에 아예 없었다.
라이트·다크 두 변형을 추가했고, 입력 토큰을 그대로 인용한 뒤 우리 데이터에 없다고 말한다.
상태 카드처럼 보이지 않게 경고 톤(앰버)으로 처리했다.

### 2.4 `Search / AI Overview` — `State=NoEvidence` (계약 §3.3)

백엔드 `POST /api/search/unified/ai-overview` 는 `no_evidence` 를 돌려주는데 대응 시안이 없었다.
추가했다. 이 상태에서는 **재시도 버튼을 두지 않았다** — 다시 눌러도 근거가 생기지 않기 때문이다.
대신 §8 의 확인 문구("최종 확인은 하이코리아 또는 1345에서 하세요")를 남겼다.

### 2.5 `Evidence / Source Card` — `LinkState` (계약 §3.5)

`LinkState: Linked | PlainText` 속성을 추가했다.
`PlainText` 는 URL 이 정부 도메인 허용 목록을 통과하지 못한 경우로,
외부 링크 아이콘을 제거하고 링크 확인 실패 사유를 문구로 밝힌다.
신뢰할 수 없는 앵커가 되느니 텍스트로 격하한다는 계약을 시안에 반영한 것이다.

### 2.6 `Result / Subcode Card` (계약 §3.4)

계약은 상위 코드 카드와 세부코드 카드를 **두 개의 별개 컴포넌트**로 요구한다.
Figma 는 이를 한 세트의 `Type=VisaStatus | SubCode` 변형으로 합쳐 두고 있었다 —
`CLAUDE.md` 의 "세부코드를 상위로 평탄화하지 않는다" 규칙과 정면으로 어긋난다.

- `Result / Subcode Card` 를 별도 컴포넌트 세트로 분리했다 (`MatchReason` × `Theme`).
- 세부코드 카드는 **상위 코드를 항상 별도의 라벨 붙은 행**으로 가리킨다 ("D-10 카드 보기 →").
- 상위 코드 카드에 `MatchReason=ParentOfExactCode` 변형을 추가하고,
  "여기 적힌 건 D-10 공통 요건이고 D-10-1 전용 요건은 세부코드 카드에 있다"는 문구를 붙였다.
- 기존 `Type=SubCode` 변형은 **전 페이지 인스턴스 0건을 확인한 뒤** 제거했다.

`MatchReason(ExactCode · ParentOfExactCode · Keyword)` 는 계약 §3.4 가 요구한 속성이다.

### 2.7 `Employment / *` 컴포넌트 5종 (계약 §3.7–3.10)

`UX-08` 에 **화면**으로만 있던 것을 재사용 가능한 컴포넌트로 뽑아 `UX-03` 에 모았다.
계약 §10 의 빌드 순서 6번 항목이다.

| 컴포넌트 | 속성 | 코드 |
|---|---|---|
| `Employment / Editable Interpretation Card` | `State(Reading·Editing·Reanalyzing)` × `HasAmbiguity` | `employment_nl.validate_extraction` · `to_analyzer_input` |
| `Employment / Clarification Card` | 단일 · 질문 1개 · 선택지 2~4개 | `employment_nl.contains_determination` |
| `Employment / Occupation Candidate` | `Rank` × `Selection` × `Certainty` | `employment_code_analyzer.mjs › searchTrack` (직종) |
| `Employment / Industry Candidate` | `Rank` × `Selection` × `Certainty` | `employment_code_analyzer.mjs › searchTrack` (업종) |
| `Employment / Final Checklist` | 단일 · HiKorea 행 고정 | — |

계약이 "절대 같게 보이면 안 된다"고 한 두 쌍을 형태로 갈라 뒀다.

- **직종 ↔ 업종** — 컴포넌트 자체가 다르고, EMERALD ↔ PERI 로 색도 다르다.
  하나의 `Track` 스위치를 둔 단일 컴포넌트로 만들지 않았다.
- **가장 가까운 후보 ↔ 확정 코드** — `NearestCandidate` 는 앰버 테두리 태그
  ("가장 가까운 후보 — 확정 아님") + 중립 카드 보더, `ConfirmedCode` 는 채운 태그
  ("HiKorea 확인 완료") + 2px 강조 보더다. 확정은 HiKorea 만 해줄 수 있기 때문이다.

`Final Checklist` 의 HiKorea 행은 다른 행과 달리 **속이 빈 링**으로 표시되고
"여기서만 확정돼요 — 이 화면에서는 완료로 표시하지 않아요" 문구를 항상 달고 있다.

---

## 3. 대조 중에 발견한 시안 결함 (수정 완료)

| 결함 | 영향 | 조치 |
|---|---|---|
| 다크 변형의 `Top` / `Badges` / `Bottom` / `Expand` 오토레이아웃 프레임에 불투명 흰색 채우기가 남아 있었다 | 다크 카드 위에 흰 막대로 렌더링 | 해당 프레임 4개의 채우기 제거 |
| 세부코드 카드가 고정 높이 120px 이라 내용이 잘렸다 | 하단 행이 보이지 않음 | 세로 hug 로 전환 |
| 혼합 채우기(mixed fills) 텍스트가 다크 변환 루프에서 건너뛰어졌다 | 다크에서 본문이 다크온다크 | 세그먼트 단위로 보정 |

---

## 4. UX-10 핸드오프 보드 갱신

### 4.1 Component Contract

10개 블록의 코드 매핑을 **실제 심볼**로 교체하고, 새로 만든 컴포넌트 10개 블록을 추가했다
(`Search / Intent Pill`, `Result / Subcode Card`, 근거 배지 3종, `Employment / *` 5종).

| 컴포넌트 | 실제 코드 |
|---|---|
| Unified Input | `assets/js/unified-search.js` › `buildUnifiedLayerHtml` |
| Interpretation Strip | `unified-search.js` › `buildInterpretationHtml` · `unified_search.py` › `classify_intent` · `build_interpretation` |
| AI Overview | `unified-search.js` › `buildAiOverviewHtml` |
| Source Card | `unified-search.js` › `buildSourceCardsHtml` · `manual_registry.py` › `evidence_gate` |
| Status / Subcode Card | `unified_search.py` › `build_organic_results` · `split_visa_code` |
| Law Lifecycle | `law_query_normalizer.py` › `classify_law_lifecycle` · `annotate_lifecycle` |
| Lookup Failure | `law_query_normalizer.py` › `evidence_status_for` · `summarize_search_outcome` |
| Employment | `employment_nl.py` › `validate_extraction` · `scripts/employment_code_analyzer.mjs` › `searchTrack` |

### 4.2 엔드포인트 정정

보드와 계획서 모두 엔드포인트를 틀리게 적고 있었다. 실제 라우트는 `backend/paradiso_backend.py` 기준:

| 틀리게 적혀 있던 것 | 실제 |
|---|---|
| `POST /api/unified-search` | `POST /api/search/unified` |
| `/api/ai-overview` | `POST /api/search/unified/ai-overview` |
| — | `POST /api/employment/interpret` |

### 4.3 Foundations — 토큰 매핑 표 추가

이게 가장 오해를 부를 뻔한 부분이다.
**Figma Foundations 의 색 값은 현재 라이브 `index.html` 값과 다르다.** 즉 제안이지 현황이 아니다.

| Figma 토큰 | CSS 변수 | 현재 라이브 (라이트 / 다크) |
|---|---|---|
| PAPER `#F7F4EF` | `--bg0` | `#F4EFE4` / `#062A22` |
| CARD_LIGHT `#FFFCF5` | `--bg1` | `#FFFCF5` / `#0C3A30` |
| LINE `#E6E6EE` | `--bd` | `#998058` / `#2D5A50` |
| DARK `#1C1F29` | `--t1` | `#073B32` / `#F4EFE4` |
| GREY `#4D5261` | `--t2` | `#3A544C` / `#C7BFA8` |
| EMERALD_TXT `#177366` | `--ac` | `#0B7357` / `#3BE4B8` |
| EMERALD_DEEP `#0B4F44` | (신설 필요) | 대응 변수 없음 |
| AMBER `#F2C879` | `--cWk` | `#E68A3A` |
| CORAL `#D95C47` | `--cy` | `#FF6B5B` / `#FF8B7A` |
| 8pt 간격 | `--sp-1..8` | 이미 일치 |

라이트 보더가 지금 **갈색(`#998058`)** 이라는 점이 특히 중요하다. 시안의 `#E6E6EE` 회색선과
전혀 다른 인상을 준다. 색을 옮길 때는 규칙마다 하드코딩하지 말고 **변수 값을 바꾼다** —
모든 `.us-*` 규칙이 이 변수를 통해 해석되기 때문이다 (계약 §6).

---

## 5. 남은 차이 · 판단 기록

### 5.1 확인 질문 선택지 개수 — 판단 완료 (2026-07)

계약 §3.8 은 "2~4개"인데 `UX-08` 화면에는 5개가 있었다.
**출입국 심사 관점에서 판단한 결과, 5개를 유지하고 계약 해석을 명확히 했다.**

근거는 인심이 아니라 정확도다.

- KSIC11 업종 코드는 수백 개다. 후보 3개짜리 닫힌 목록에 신청인의 실제 사업이
  들어 있지 않은 경우가 흔하다.
- "직접 입력"을 없애면 사용자는 **셋 중 가장 덜 틀린 것**을 고를 수밖에 없다.
  그렇게 나온 업종 코드는 확정 코드가 아닌데도 최종 체크리스트를 타고
  하이코리아 신고 화면까지 그대로 전달된다. 이건 계약이 §3.9 에서
  ("가장 가까운 후보 ≠ 확정 코드") 막으려던 실패 자체다.
- 심사자 입장에서는 신청인이 직접 적은 "PC방"을 읽는 편이,
  목록에 없어서 고른 "일반 음식점"을 읽는 것보다 언제나 낫다.
- "잘 모르겠어요"(판단 보류)와 "직접 입력"(목록에 없음)은 **서로 다른 정보**다.
  둘을 합치면 후보 세트가 부족했다는 유일한 신호가 사라진다.

**조치:** 2~4개 제한은 **실질 후보 답변에만** 적용한다고 계약 §3.8 에 명시했다.
탈출 경로 2종은 답변 후보가 아니므로 세지 않되, **점선 그룹("이 중에 없다면")으로
시각적으로 분리**해 후보처럼 보이지 않게 했다.
`Employment / Clarification Card` 컴포넌트와 `UX-08` 화면 양쪽에 같은 구조를 적용했다.

### 5.2 계속 기록해 두는 차이

- `Search / Interpretation Strip` 의 `HasUnknownCode` 는 불리언 속성이 아니라
  `State=UnknownCode` 변형으로 표현했다. 계약 문구와 형태가 다르므로 여기에 적어 둔다.
- 계약 §3.5 의 `SourceType` 열거값(`OfficialPortal` · `OfficialLaw` · `OfficialHelpline` ·
  `Manual` · `Precedent` · `Structured`)과 Figma 의 `Type` 8종은 **입도가 다르다.**
  Figma 쪽이 더 잘게 쪼개져 있다 (`Statute` · `Decree` · `Rule` → `OfficialLaw`,
  `HiKorea` · `Embassy` → `OfficialPortal`, `ParadisoData` → `Structured`).
  구현할 때 이 대응표를 쓰면 되며, 굳이 Figma 를 뭉갤 필요는 없다고 판단했다.

---

## 6. 이 문서를 쓸 때 지킨 것

- 법령·이민 내용을 새로 만들지 않았다. 문구는 계약 §8 의 확정 카피를 그대로 쓰거나
  기존 시안 문구를 옮겼다.
- 면책·출처 경고·불확실성 고지를 축소하거나 지우지 않았다.
- 제거는 단 한 건(`Type=SubCode` 변형)이고, 전 페이지 인스턴스 0건을 확인한 뒤에 했다.
  같은 내용은 `Result / Subcode Card` 에 더 정확한 형태로 남아 있다.
