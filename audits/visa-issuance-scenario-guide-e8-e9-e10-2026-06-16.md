# 사증발급 시나리오 안내 팝업 + E-8·E-9·E-10 사증발급 정비 — 감사 (2026-06-16)

## 목표 (사용자 요청 2건)
1. **사증발급 시나리오 안내 팝업**: 각 체류자격은 세부코드·국적에 따라 필요한
   서류·절차가 다른데, 사증발급(처음 외국인을 데려오는 단계) 설명이 빈약했음.
   유저의 시나리오를 확인하면 경로(서류·절차)를 알려주는 팝업 UI를 구축. 법령/매뉴얼
   근거로 내용을 채움.
2. **E-8·E-9·E-10 정비**: 세 자격의 "처음 데려오는 사증발급" 서술이 사실상 사용
   불가 수준으로 빈약 → 매뉴얼 근거로 보강. **E-9 필수서류 오류 점검·수정.**
   E-8~E-10 이용자 특성을 고려해 **UI를 최대한 user-friendly하게** 설계.

이 작업은 렌더러/데이터 위생 작업이며, 법적 완전성을 주장하지 않습니다. 법령·매뉴얼
내용을 발명하지 않았고, 로컬 출처에 없는 서류요건을 추가하지 않았습니다.

## 근거 출처 (로컬)
- `docs/data/claude_opus_manual_extraction_2026_05/visa_hwp_full.txt`
  (2026.5 사증발급 안내매뉴얼 전문 추출본)
  - **E-8 계절근로** §26 (278–283p): 제출서류 9709–9719줄, 사증발급인정서/지자체
    신청 9657–9672줄, 세부코드 표 9674–9707줄.
  - **E-9 비전문취업** §27 (284–293p): 고용허가제·17개국 9724–9732줄, 허용업종표
    9745–9818줄, **첨부서류(공통서류/업종별 추가서류) 9881–9914줄**,
    범죄경력증명서·건강상태확인서 9827/9842/9848줄.
  - **E-10 선원취업** §28 (294–296p): 활동범위 10117–10123줄, 범죄경력·건강
    10132–10146줄, **첨부서류 10189–10212줄**, 대행기관(해운조합/수협) 10184–10185줄.
- 평가 등급(evidenceLevel)·페이지 근거: `data/procedure_evidence_bindings.json`
  (E-8·E-9·E-10 모두 `source_confirmed`).

## 1) E-9 "필수서류 잘못" — 근본 원인과 수정 (보호 파일 surgical 수정)
### 근본 원인
보호 데이터 `visa_data.json`·`backend/data/visas.json`의 **E-9** 레코드가
사증발급(입국 전) 최초신청 서류에 **유학(D-2/D-4) 서류**를 잘못 매핑하고 있었음:
- `documents_initial` 4번째 항목 = `표준입학허가서 또는 재학/수료증명서`
- `initialReqDocs` / `newReqDocs` 에 `doc_enroll`(= "표준입학허가서 또는 재학/수료증명서")
- `newReq` 프로즈에 "사전교육 수료증"

이 `doc_enroll` 항목이 사증발급 탭의 기본 준비서류 그리드에 그대로 노출되어,
**비전문취업(노무) 비자에 학생 서류가 뜨는** 명백한 데이터 오류였음.

### 수정 (사용자 명시 승인 — "점검 후 수정")
보호 파일 2개에 **단일 항목 surgical 교정**(CLAUDE.md "safe, surgical edits"):
잘못된 학생 서류를 E-9의 핵심 서류인 **고용허가서**(`doc_eps` =
"고용허가서 사본 (고용노동부 발급)")로 교체. 고용허가서는 매뉴얼 E-9 공통서류
("고용허가서 및 표준근로계약서 사본")이자 E-9 연장서류에 이미 쓰이는 ID라
발명이 아닌 **충실한 교정**임.

| 필드 | 변경 전 | 변경 후 |
|---|---|---|
| `newReq` | 표준근로계약서(EPS), 사업자등록증, 건강검진서, **사전교육 수료증.** | **고용허가서(고용노동부 발급)**, 표준근로계약서(EPS), 사업자등록증, 건강진단서. |
| `newReqDocs` / `initialReqDocs` | …, doc_health, **doc_enroll** | **doc_eps**, doc_emp_contract, doc_biz_reg, doc_health |
| `documents_initial` | …, **{표준입학허가서 또는 재학/수료증명서}** | **{고용허가서 사본, 고용노동부 발급}**, 표준근로계약서, 사업자등록증, 의료기관 건강진단서 |

두 보호 파일은 indent=2로 round-trip byte-stable임을 확인 후, **E-9 필드만** in-place
수정 → git diff는 E-9 줄(파일당 17줄)만 변경. 다른 41개 레코드·다른 절차·면책/주의/
출처 문구는 일절 변경 없음.

## 2) E-8·E-9·E-10 사증발급 콘텐츠 보강 (`data/visa_issuance_records.json`, 비보호)
각 자격을 **세부코드/업종/선박종류별 다중 모드(issuanceModes)** 로 재구성(매뉴얼 근거).
첫 모드는 렌더 계약(공통서류≥1·steps·sourceRefs 페이지근거)을 충족하도록 정렬.

- **E-9 비전문취업 (7개 업종 모드)**: 🏭제조업·🏗️건설업·🌾농축산업·🎣어업·🍽️서비스업·
  🌲임업·⛏️광업. **공통서류**(사증발급인정신청서 별지21호·여권·사진·사업자등록증·
  고용허가서및표준근로계약서·사업장실태조사서) + **업종별 추가서류** + **사증신청단계
  서류**(범죄경력증명서 3개월이내·건강상태확인서). 절차 3단계(고용허가→인정서 신청
  →공관 사증). 17개국·대행기관(제조-중기중앙회/건설-대한건설협회/어업-수협/농축산-농협)
  안내.
- **E-8 계절근로 (5개 추천경로 모드)**: 🤝MOU지자체·👪결혼이민자친척·🔁G-1재입국·
  🎓유학생부모·🗣️언어도우미. 공통서류(표준근로계약서·내국인구인노력·여권사본·숙소시설표)
  + 경로별 추가서류. **지자체가 비자포털로 사증발급인정서 신청** 강조, 단수사증 8개월.
- **E-10 선원취업 (3개 선박 모드)**: 🚢내항상선·🐟어선·🛳️순항크루즈. 공통서류
  (사증발급인정신청서·여권·사업자등록증·사진·표준근로계약서·신원보증서·고용신고수리서)
  + 선박별 추가서류(면허·등록증·고용추천서) + 범죄경력·건강상태. 대행기관(해운조합/수협).

요약문에서 기존 "POC … 후속 추출 대상" 등 placeholder 문구 제거. 모든 모드는
`source_confirmed` 페이지 근거(E-8 278–283 / E-9 284–293 / E-10 294–296) 보유.

## 3) 팝업 UI (렌더러 — `index.html`)
사증발급은 이미 절차별 안내의 `PROCEDURE_CONFIG[0]`(visaIssuance)로 통합돼 있음. 그 위에
**시나리오 안내 팝업**을 추가:
- 레코드가 `scenarioGuide:true` + 모드≥2 이면, 모든 카드를 한꺼번에 쏟지 않고
  **친절한 단일 질문형 선택 UI** 렌더(`renderIssuanceScenarioPicker`).
  큰 질문 + 🧭"내 상황 고르기" 트리거 → 모달(`#issuanceGuideOverlay`)에서 **큰 아이콘 +
  큰 글씨** 버튼으로 하나 선택 → 해당 시나리오 카드만 표시(`issuance-needs-pick` 게이팅).
- **E-8~E-10 user-friendly 설계**: 한 번에 하나씩 고르는 흐름, 이모지 아이콘, 큰 글씨,
  plain-language 질문("어떤 일(업종)을 하러 오시나요?" / "어떤 방법으로 추천받았나요?"
  / "어떤 배에서 일하나요?"), 인지부담 최소화.
- 시나리오 안내 자격은 **팝업이 서류의 단일 출처**가 되도록 상단 기본 서류 그리드·서류
  수·요약·검토안내를 생략(위/아래 중복 노출 방지). 카드의 공통+업종별 서류가 권위 출처.
- 기존 모달/포커스트랩/ESC/백드롭/외부클릭 인프라(`openModal`/`closeModal`) 재사용 —
  새 동작 모델 미추가. 트리거 `aria-haspopup="dialog"`, 모달 `role="dialog" aria-modal`,
  선택지 `aria-pressed`, 카드 의미론적 heading 유지.
- **F-4 영향 없음**: 재외동포 전용 route guide는 그대로(generic 사증발급에서 제외 유지).
  나머지 38개 단일모드 자격은 기존 렌더 그대로(회귀 없음).

신규 함수: `renderIssuanceScenarioPicker`, `openIssuanceGuide`, `chooseIssuanceMode`,
`applyIssuanceModeSelection`, `clearIssuanceGuide`. 모드 카드 제목에 이모지 아이콘 옵션
추가. i18n 키 6개(`issuanceGuide*`)를 ko/en/zh-CN 동일하게 추가.

## CLAUDE.md 준수
- 보호 파일: `visa_data.json`·`backend/data/visas.json`는 **E-9 단일 오류 항목만**
  surgical 교정(승인됨). `doc_master.json` 미변경.
- 서브코드를 부모로 평탄화하지 않음. 사증발급↔체류 절차 혼합 없음(전부 사증 매뉴얼 출처).
- 법령/요건 발명 없음. 표시 서류는 모두 2026.5 사증 매뉴얼 해당 페이지 근거.
- 면책·주의·출처·불확실성 문구 유지/강화(각 모드 warnings + disclaimer + 근거 보기).

## 검증 (전부 통과)
```
node scripts/check_visa_issuance_ui.mjs                 → 2846 checks, 0 failures (41 non-F-4)
node scripts/validate_visa_issuance_enrichment.js       → 445 passed, 0 warnings, 0 failed
node scripts/check_visa_issuance_scenario_guide.mjs(신규) → 166 checks, 0 failures
node scripts/check_i18n.js                              → OK (1054 keys match ko/en/zh-CN)
node scripts/check_i18n_coverage.mjs                    → OK (1054 keys)
node scripts/smoke_static_i18n.mjs                      → OK (inline scripts parse)
node scripts/check_index_hardcoded_text.mjs            → OK
node scripts/check_f4_route_guide.mjs                  → 83 checks, 0 failures
node scripts/check_static_visa_result_cards.js         → OK
node scripts/check_placeholder_suppression.js          → 19 passed, 0 failed
node scripts/check_subcode_modal.mjs / check_dummy_text.mjs → OK
node scripts/check_priority_status_journeys.js / remaining / d2 / procedure_journey → 모두 PASS
python3 scripts/check_visa_data_text_integrity.py / check_visa_text_corruption.py → PASS
python3 scripts/check_required_documents_coverage.py / check_doc_master_integrity.py → PASS
git diff --check → clean; bash -n scripts/check_repo.sh → OK
```
신규 스모크 `check_visa_issuance_scenario_guide.mjs` + 기존 issuance 검증 2종을
`scripts/check_repo.sh` `[9e/14]` 섹션에 등록(기존엔 CI 미포함이었음) → CI 보호.

렌더 확인: 실제 `renderIssuanceScenarioPicker`를 추출 실행 → E-9 7모드/E-8 5모드/
E-10 3모드의 게이팅 팝업 구조(질문·트리거·모드별 카드 wrap·choice 라벨) 생성 확인,
E-9 issuance 전 영역에 학생 서류 문자열 없음·공통서류에 고용허가서 포함 확인.

## 알려진 한계
- 헤드리스 브라우저가 없어 픽셀 스크린샷은 없음(이전 PR과 동일). 실제 렌더 함수 실행 +
  정적/데이터 스모크로 검증.
- 다른 38개 자격은 단일 모드 유지(시나리오 팝업 미적용) — 매뉴얼 근거가 확인된
  E-8/E-9/E-10부터 적용. 추후 자격별 다중 모드는 검증된 출처가 있을 때 확장(발명 금지).
- 국적(고용허가제 17개국·MOU 등)은 현재 warnings/안내로 표기. 별도 국적 선택 단계는
  공식 오버레이(`official_web_overlays.json`)가 검증되면 후속 확장.
- **(기존 이슈, 본 작업과 무관)** `scripts/check_scenario_help_records.py`는 HEAD에서도
  동일하게 실패(store 레코드 순서 vs visa_data 순서 불일치, index0 store=K-ETA).
  본 PR은 `scenario_help_records.json`·레코드 순서를 변경하지 않았으며 별도 이슈로 분리.
