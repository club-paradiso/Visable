# Short-stay checker — 제주만 방문(제주 무사증 대상) 오탐 수정 + 팝업 UX (2026-06)

## 요청 (사용자)
1. "국적별 단기입국 경로 확인"에서 **명백히 "제주무사증" 대상**인 국적이 [방문 지역]을
   **"제주만 방문"(`jeju_only`)** 으로 선택했는데도 **"공식 확인이 필요한 사례입니다"** 팝업이
   뜨는 오류 → 명백한 제주 무사증 대상자가 제주만 방문할 때는 **확실하게 제주 무사증 대상**임을
   안내하도록 수정.
2. 전반적인 **화면 내 팝업(모달) UI를 좀 더 user friendly**하게.

## 원인 분석
`assets/js/short-stay-checker.js`의 `jeju_only` 분기에서, 일반 무사증(B-1/B-2-1) 비대상이지만
**제주 무사증 입국불허 목록에 없는**(즉 명백한 제주 무사증 대상) 국적의 결과 상태를
`needs_official_check`로 설정 → `computeVerdict()`가 이를 `check` 톤으로 매핑하여
**"공식 확인이 필요한 사례입니다" ⚠️** 헤드라인을 출력. 데이터(`b22Jeju.jejuEntryDenied === false`)
는 대상임을 명확히 말하는데 평결만 불확실하게 표시되던 문제.

## 근거 (저장 출처 기준 — CLAUDE.md 준수)
- `data/short-stay/rules.json` 각국 `b22Jeju.jejuEntryDenied`(법무부고시 제2022-189호 사본 시드):
  `false` = 제주 무사증 입국불허 국가 아님 = **제주 무사증(B-2-2) 대상**.
- 새로운 법적 요건을 발명하지 않음. **렌더러(checker) 차원에서만** 명확한 사실을 오해 없이 표현.
- 면책·주의·최신성 경고는 그대로 유지(제주 한정 별도제도, 인정 입국경로 확인, 입국심사관 결정,
  출처 최신성 등은 "반드시 확인할 점"에 계속 노출).

## 변경 내용

### 1) 평결 로직 — `assets/js/short-stay-checker.js`
- `jeju_only` + 제주 무사증 대상(불허 목록 미포함) 분기의 상태를
  `needs_official_check` → **신규 `jeju_visa_free`** 로 변경.
- `path`: `'제주 무사증(B-2-2) 경로 확인'` → **`'제주 무사증(B-2-2) 무비자 입국'`**.
- 설명 문구를 단정형으로: "…사증 없이 제주 무사증(B-2-2)으로 입국할 수 있습니다(체류 30일).
  단, 제주 직항 등 제주 무사증이 인정되는 입국경로(항공편·선편)로 들어와야 합니다."
- `computeVerdict()`에 `jeju_visa_free` 케이스 추가 → 긍정 톤 `jeju`,
  헤드라인 **"제주 무사증으로 제주를 방문할 수 있습니다"** (🛫, 녹색 계열).
- `statusBadge()` / `toneClass` / `toneIcon` / CSS(`.ssc-status-jeju`,`.ssc-verdict-jeju`) 추가.

### 2) 팝업 UX
- 결과 렌더 후 평결 블록을 부드럽게 스크롤 노출(`revealResult()`, prefers-reduced-motion 존중) —
  좁은 화면에서 폼이 그대로인 듯 보이지 않고 답이 바로 보이도록.
- `index.html` `.modal-close`(전 모달 공통): 원형 호버 타깃 + 호버 배경 + `:focus-visible`
  아웃라인으로 닫기 버튼 식별성/접근성 향상.

## 검증
- `node scripts/check_short_stay_rules.mjs` → **78 checks, 0 failures**.
- 시나리오: 베트남·중국(제주만) → `jeju_visa_free` / "제주 무사증으로 제주를 방문할 수 있습니다",
  네팔(불허) → `visa_required`, 일본(일반 무사증) → `likely_available` (변동 없음).

## 영향 없음 / 유지
- `jeju_then_mainland`(제주→본토) 분기 로직과 일반 무사증/사증 필요 분기는 변경 없음.
- 보호 데이터 파일(`visa_data.json`,`backend/data/visas.json`,`doc_master.json`) 미수정.
- 모든 면책·주의·최신성 경고 유지(약화 없음).
