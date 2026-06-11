# 매뉴얼 추출 고도화 · RAG 후속 계획 (PHASE 12 — 미래 계획, 본 패치 범위 아님)

목표: 출입국 안내매뉴얼(HWP) → 구조 보존 추출 → 조항 단위 청크 → 검색 기반 근거 주입(RAG).
파인튜닝은 사용하지 않는다(법령·매뉴얼은 개정 주기가 짧아 가중치에 굽는 방식이 부적합).
구조화 청크에 대한 retrieval로 대응한다.

## 1. HWP → DOCX
- 변환기: `hwp5proc`(pyhwp) 또는 LibreOffice `soffice --headless --convert-to docx`
  (한컴 HWPX는 hwpx → OOXML 직변환 우선). 변환 산출물은 `docs/source-manuals/converted/`에
  버전·해시와 함께 보관, 원본 HWP는 불변.
- 수용 기준: 페이지 수 ±2 이내, 표 개수 보존율 ≥ 95% (샘플 20표 수동 대조).

## 2. DOCX XML 추출
- `python-docx` 대신 OOXML 직접 파싱(`w:tbl`/`w:tr`/`w:tc`, `w:pStyle`)으로
  병합셀(`w:vMerge`, `gridSpan`)과 표 계층을 그대로 캡처.
- 산출 스키마(JSONL): `{doc_id, page_hint, heading_path[], block_type(paragraph|table|cell),
  table_id, row, col, rowspan, colspan, text, style}`.

## 3. 표 처리
- 평탄화 금지: 셀 단위 레코드 + (행 헤더, 열 헤더) 경로를 함께 저장.
- 현재 `[[TABLE]]` 텍스트 추출의 손실 사례(체류기간 상한표, 어학요건표, 수수료표)를
  회귀 테스트 픽스처로 고정.

## 4. 계층 메타데이터
- heading_path 예: `["체류자격별 안내", "10. 유학(D-2)", "체류기간 연장허가", "다. 제출서류"]`.
- 절차 도메인 태그: `visa_issuance` | `stay_sojourn` (사증/체류 매뉴얼 혼입 금지 —
  현행 도메인 분리 규칙을 청크 레벨로 승계).
- 코드 태그: 본문에서 `[A-Z]-\d(-\w+)?` 추출 + 상위코드 정규화(D-2-1→D-2)는
  분류용 보조 필드로만 (subcode를 parent로 평탄화하지 않음).

## 5. 청크 전략
- 1청크 = 1 최소 의미 단위: "코드 × 절차 × 표제(제출서류/대상/심사기준)" 블록.
  표는 셀-그룹(행 단위) 청크 + 표 전체 요약 청크 이중화.
- 메타: `{status_code, sub_codes[], procedure_type, source_heading, manual_version,
  page_range, revision_date, hash}`.
- 크기 가이드: 200–700자(한국어), 표 행 청크는 예외 허용.

## 6. RAG 파이프라인
- 1단계(무벡터, 즉시 가능): 현행 `structured_requirements_*.json` 인덱스에
  BM25/keyword 검색(코드·절차·표제 가중)을 붙여 `_select_grounding()`을 일반화.
- 2단계(벡터): bge-m3 또는 KoSimCSE 임베딩 + SQLite-VSS/pgvector(이미 Supabase env 훅 존재).
  하이브리드(BM25+벡터) 상위 k=6 → 코드/절차 필터 → 프롬프트 주입.
- 답변 계약: 고위험 주장(자격요건·서류·기한·수수료·취업제한·변경/연장 요건) 옆에
  청크 인용(`매뉴얼명·판·페이지·표제`)을 의무 표기. 검색 실패 시 기존
  소스-불가 경고(본 패치에서 추가) 문구를 그대로 사용.
- 평가: `backend/data/eval/paradiso_ai_golden_questions.json` 확장 +
  인용 정확도(청크-답변 일치) 자동 채점 스크립트.

## 7. 갱신 운영
- 분기별 매뉴얼 개정 시: 변환→추출→청크 재생성→`manual_version` 증가→
  diff 보고서(추가/삭제/변경 청크)→골든 질문 회귀→배포.
- 기존 `scripts/sync_visa_data.py`·check_repo 게이트에 청크 해시 검증 단계 추가.

비고: 본 계획은 Railway 아키텍처를 교체하지 않고 백엔드 내 검색 모듈 확장으로 수용 가능.
판례/유권해석(`precedent_sources` 스캐폴드) 배선은 법령 RAG 안정화 이후 별도 단계로.
