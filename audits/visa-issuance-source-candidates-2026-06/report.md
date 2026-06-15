# 사증발급 제출서류 출처 검증 — 검토용 후보셋 (2026-06)

## 무엇인가
사용자 요청("전체 체류자격을 reliable source로 실제 검증해 `source_confirmed` 승격")에
대한 **안전한 1단계 산출물**. 매뉴얼 원문에서 사증발급(visa_issuance) 첨부/제출서류를
추출한 **사람 검토용 후보 데이터**.

- 파일: `candidates.json` (37개 체류자격, schema candidate-1.3)
- **보호파일(`visa_data.json`) 미반영, 사용자 화면 미표시, 신뢰도 플래그 미변경.**

## 왜 바로 승격하지 않았나 (확인된 사실)
1. **데이터 공백**: `procedures.visaIssuance.requiredDocs`가 **37개 중 35개에서 비어
   있음**(채워진 것은 C-3, F-6뿐). 빈 레코드를 `source_confirmed`로 올리면 "없는
   서류"를 검증됐다고 표시하는 **허위**.
2. **법령 텍스트 한계**: 보유 시행규칙 조문 텍스트는 별표/별지서식 미포함. 유일한
   문서표 `[별표 5]`는 사증발급 범위 + OCR 잡음 → 체류 절차 확정 근거로 부적합.
3. **공식 매뉴얼의 재량성**: 2026.5 매뉴얼이 "청장이 제출서류를 **가감 가능**, 본
   매뉴얼은 보조자료"라고 명시(본 후보셋 37개 중 **20개 섹션에서 해당 문구 확인**).
   → "관할 기관 확인" 류 고지는 사실과 부합하므로 유지가 옳음.
4. **OCR 추출 신뢰도**: 매뉴얼은 스캔 PDF. 텍스트 추출은 가능하나 섹션별 잡음 가능 →
   **사람이 인용 page로 원본을 대조**해야 권위 있는 확정.

## 추출 방법
- `visa_manual_2026_05.pdf`를 pdfminer.six로 텍스트화(484p) 후 섹션별 문서표제어
  **첨부서류 / 제출서류 / 신청서류 / 구비서류**(OCR 띄어쓰기 허용) 발췌.
- 섹션 페이지 범위는 매뉴얼 목차·러닝헤더로 매핑.

## 후보셋 구조 (`candidates.json`)
레코드별:
- `code`, `name`
- `sectionPageStart` / `sectionPageEndExclusive` — **신뢰 가능**(원본 PDF 검토 시작점).
- `boundaryApproximate` — E-5/E-6/F-4/H-2는 OCR상 경계가 불명확하여 true.
- `noDocsExpected` — B-1(사증면제)·B-2(관광통과)는 제출서류 없음(정상).
- `officerDiscretionDisclaimerFound` — "첨부서류 가감 가능" 공식 문구 존재 여부.
- `submissionDocExcerpts[]` — `{page, excerpt}` **verbatim OCR 발췌(보조자료)**.

## 현황 (coverage)
- 37개 레코드. **발췌 확보 35개** + **제출서류 없음(정상) 2개(B-1, B-2)** = 37 전수 처리.
- 공식 재량 고지 확인 **20개** 자격.
- 발췌 예시(정확): D-8/F-2/F-5는 "사증발급신청서(별지 제17호), 여권, 표준규격사진,
  수수료 + 자격별 추가서류" 형태로 깔끔 추출됨.

## 권장 후속 워크플로(승인 후)
1. 각 레코드 `page`로 **원본 PDF 해당 페이지를 직접 확인**(권위 있는 단계).
2. 실제 첨부서류 확정 — 공통(사증발급신청서·여권·표준규격사진·수수료) + 자격별 추가.
3. 승인 건만 `visa_data.json`의 `procedures.visaIssuance.requiredDocs`를 **surgical**
   채움(보호파일 — 최소·정밀 수정, 검토자 사인오프 권장).
4. `data/procedure_evidence_bindings.json`의 해당 `visa_issuance` 바인딩을
   `source_confirmed`로 승격하되 **매뉴얼 page 인용** + `sourceBackedFields` 정직 표기
   (`documents:true`는 실제 채워 검증한 경우에만).

## 안전성 원칙(준수)
- 읽기 전용 산출물. 사용자 노출·보호파일·신뢰도 플래그 무변경.
- 법적 서류내용을 **창작하지 않음**(매뉴얼 원문 발췌 + page 인용만).
- 확정 표기는 사람 검토 후에만(CLAUDE.md "법적 정확성 단정 금지" 준수).

## 비고 — visa.go.kr
사용자가 요청한 visa.go.kr/HiKorea 직접 수집은 본 실행 환경의 **네트워크 egress
허용목록**에 해당 호스트가 없어 차단됨(curl·WebFetch 모두 403). 접근 허용(커스텀
allowlist 환경) 시, 헤드리스 Chromium으로 SPA 렌더·추출해 `official_web_overlays.json`
규칙(국가/공관 보완, 매뉴얼 미덮어쓰기)대로 적용 가능.

## PILOT 적용 결과 (F-2, D-8)
visa.go.kr 차단으로, 사용자 승인(검토용 후보셋 우선)에 따라 **읽기 가능한 매뉴얼 원문**
으로 2개 자격을 end-to-end 적용. **보호파일(`visa_data.json`·`doc_master.json`)은
변경하지 않고**, 사증발급 출처-그라운딩 전용 **비보호 파일**만 수정:
- `data/visa_issuance_records.json`
  - **F-2(거주)**: 기존 레코드의 모호한 서류("세부 유형별 자격 입증자료")를 매뉴얼
    원문(308–313p) 기준 공통/추가/조건부 서류로 보강.
  - **D-8(기업투자)**: 신규 레코드 생성(102–116p 기준 신청절차·공통/추가/조건부 서류,
    매뉴얼 page sourceRefs 포함).
- `data/procedure_evidence_bindings.json`
  - F-2·D-8 `visa_issuance` 바인딩을 `limited` → **`source_confirmed`**로 승격
    (manualSources page 인용, sourceBackedFields 정직 표기, 한계 안내문 유지).

검증: `validate_visa_issuance_enrichment.js` 275 pass / 0 fail,
`check_source_grounding_metadata.py` OK, `check_placeholder_suppression.js` 19/19,
헤드리스 Chromium 렌더로 두 자격 모두 배지 "공식근거 직접 확인"(source_confirmed)
+ 매뉴얼 page + 실제 서류 표시 확인.

비고: 본 승격은 매뉴얼 인용 페이지 기반의 기계 추출(extractionConfidence=medium)이며,
세부유형·수수료·처리기간은 한계 안내문으로 관할기관 확인을 명시. 사람 spot-check 후
나머지 자격으로 확대 가능.

## 전체 롤아웃 결과 (사증발급 source_confirmed 9 → 32)
파일럿 검증 후 사용자 지시로 나머지 `limited` 자격까지 동일 방식으로 확대 적용.
모두 **비보호 파일**(`data/visa_issuance_records.json`, `data/procedure_evidence_bindings.json`)
만 수정, 매뉴얼 인용 페이지 포함.

승격(23): C-1, C-4, D-1, D-3, D-5, D-6, D-7, D-9, E-1, E-2, E-3, E-4, E-5, E-6,
E-9, E-10, F-1, F-3, F-5, G-1, H-1, A-2, A-3
(신규 레코드 20 + 기존 보강 3[E-9·F-1·G-1]). 파일럿(F-2·D-8) 포함 총 source_confirmed 32.

이질적 자격(F-1·F-5·G-1·H-1 등)은 공통서류만 확정 표기하고 세부유형 차이를 한계
안내문으로 명시. 별지 제17호(사증발급) vs 별지 제21호(사증발급인정) 구분 반영.

보류(limited 유지):
- **A-1(외교)**: 표준 첨부서류 목록이 아닌 외교절차(구상서 등) 특수 — 별도 검토.
- **F-4(재외동포)**: 외국국적동포 특수 절차(한국어능력·범죄경력·국적입증 등) — 별도 검토.
- 특수 트랙(D-4-1, D-4-2K, K-STAR, REGION-S, YOUTH-STAY): 지역특화/신설 제도 — 별도 검토.

검증: `validate_visa_issuance_enrichment.js` 375 pass / 0 fail,
`check_source_grounding_metadata.py` OK, placeholder suppression 19/19,
헤드리스 Chromium 렌더로 표본(D-7·E-9·H-1 등) 모두 "공식근거 직접 확인" + 매뉴얼
page + 실제 서류 표시 확인. 보호파일(`visa_data.json`·`doc_master.json`) 무변경.

권고: 본 23건은 매뉴얼 인용 페이지 기반 기계추출(confidence=medium)이므로,
인용 페이지 대조 사람 spot-check 후 보류 항목(A-1·F-4·특수트랙)으로 확대 권장.
