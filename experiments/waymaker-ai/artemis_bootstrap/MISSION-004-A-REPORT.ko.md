# Waymaker Artemis Mission 004-A 실행 보고서: 독립적 AI 응답 평가 인프라 구축

2026-10-29 · Artemis Mission 004-A 실행 기록. 운영 코드 및 실제 데이터는 변경하지 않았다.

---

## 1. 결론 및 핵심 요약

- **독립적 AI 응답 평가 인프라 구축 완료:** Artemis의 기존 실험 시스템(`trust_gate`, `procedure_route`, `smoke_grader`, `metrics`)을 온전히 재사용하고 중복 구현을 배제한 독립 평가 프레임워크(`artemis_bootstrap/artemis_eval.py`)를 완성했다.
- **새로운 평가 데이터 스키마 및 Validator 구현:** `schemas/artemis_eval_item.schema.json`에 Draft 2020-12 호환 스키마를 정의하고, SHA-256 무결성 해시 대조, 증거 식별자 정합성, 절차 상호배타성을 표준 라이브러리만으로 엄밀히 검사하는 결정론적 검증기(`validate_dataset`, `validate_eval_item`)를 구현했다.
- **4대 핵심 평가 차원 채점 체계 확립:**
  1. **출처 충실도 (Source Fidelity):** 승인된 출처 내 사실 부합성, 금액·기간·날짜 날조(환각) 차단, 미승인 출처 왜곡 유출 탐지.
  2. **인용 정확성 (Citation Accuracy):** 필수 근거 인용 여부, 미존재 가짜 ID 인용 차단, 미승인 출처 인용 방지, Precision/Recall 정량화.
  3. **절차 오류 방지 (Procedural Integrity):** 사증발급(visa_issuance)과 체류절차(stay)의 영역 혼합 차단, 절차 모호 질의에 대한 되묻기(Clarify) 강제.
  4. **부적절한 보류 방지 (Abstention Appropriateness):** 충분한 근거가 있음에도 침묵하는 과도한 보류(Inappropriate Withholding) 차단 및 근거 부재 시 올바른 보류(Appropriate Withholding) 동시 검증.
- **가상 대표 평가 문항 10선 구축:** 실존 인물 정보나 법령 왜곡 위험이 전혀 없는 가상 행정·체류자격(Z-9, X-1 등) 기반 평가 데이터셋(`artemis_eval_cases_10.json`)을 구축하고 전 문항 SHA-256 무결성 검증을 통과했다.
- **완벽한 테스트 및 회귀 검증:**
  - 신규 자동화 테스트 26개 작성 (`test_artemis_eval_infrastructure.py`) → 26개 전원 통과 (0.13초).
  - Artemis 관련 테스트 346개 전원 통과 (11.89초).
  - `waymaker-ai` 패키지 전체 회귀 테스트 1,388개 전원 통과 (19.83초, 실패 0건).
- **무결점 실행 환경:** 유료 API 호출 없음, Gemma 4 E4B 가중치 다운로드 없음, 운영 서버 무영향, 표준 라이브러리 기반 100% 재현성을 확보했다.

---

## 2. 작업 원칙 및 제약 조건 준수

| 항목 | 준수 현황 | 증빙 |
|---|---|---|
| 작업 브랜치 | `feat/artemis-mission004-gemini`에서만 작업 | `git branch` 확인 완료 (`main` 보호) |
| 기존 문항 보존 | 기존 벤치마크 및 정답 일체 수정 없음 | `v0/*.jsonl`, `smoke_cases.json` 등 원본 불변 |
| 법률 판단 승인 | AI 생성 판단을 사람 승인으로 표시하지 않음 | 신규 문항 모두 `is_synthetic: true`, `synthetic_fixture` 명시 |
| 운영 환경 보호 | 운영 서버(`/api/ask`) 및 실제 사용자 데이터 미수정 | `experiments/` 내 격리 파일만 생성 |
| 모델 및 API | Gemma 4 미다운로드, 유료 외부 API 미사용 | 표준 라이브러리 및 로컬 결정론적 파서만 사용 |
| 채점 기준 엄격성 | 테스트 통과를 위한 기준 완화 배제 | 단위·역할·인용 일치 엄격 적용 |

---

## 3. 재사용된 기존 아키텍처 및 중복 배제

새로운 평가 인프라를 바닥부터 다시 작성하지 않고, 이미 검증된 Artemis 핵심 엔진을 모듈식으로 재사용했다.

1. **`trust_gate.py` 재사용:**
   - 문단 단위 암호학적 해시 검증(`approval_hash`) 및 승인 상태 확인(`is_trusted`, `DIRECT_EVIDENCE_STATES`).
   - 정밀 사실 추출기(`extract_claims`): 금액, 기간, 날짜, 서류 명칭 추출.
   - 근거 지지성 판정(`_supported`): 승인 텍스트와 추출 클레임 간 정규화 대조.
2. **`procedure_route.py` & `waymaker_ai.contracts` 재사용:**
   - 절차 분류 엔진(`procedure_scope`): `visa_issuance`와 `stay` 범위의 분리 규칙 계승.
   - 상호 혼합 방지(Visa/Stay cross-contamination prevention).
3. **`smoke_grader.py` 재사용:**
   - 울타리형(Fence) 및 나체형(Bare) JSON 객체 파서(`parse_output`).
   - 금액 단위 및 한글·외화 정규식(`MONEY_RE`).
4. **`waymaker_ai.evaluation.metrics` 설계 원칙 계승:**
   - `CORRECT`, `WRONG`, `NOT_SCORABLE` 3원 결과 체계.
   - 텍스트 유사도(Similarity) 배제 및 결정론적 일치 검사 원칙 적용.

---

## 4. 구현 상세

### 4-1. 평가 데이터 스키마 (`schemas/artemis_eval_item.schema.json`)
Draft 2020-12 스키마 규격을 충족하며 다음 구조를 보장한다.

- `id`: `^[A-Za-z0-9_-]{3,64}$` 정규식 준수.
- `dimension`: `source_fidelity`, `citation_accuracy`, `procedural_integrity`, `abstention_appropriateness`, `composite` 중 하나.
- `evidence`: 개별 근거 블록마다 `id`, `title`, `text`, `source` 필수. `source.approval_state`(`approved`, `community` 등), `source.domain`(`visa_issuance`, `stay`, `general`) 및 `source.approved_sha256` 포함.
- `expected`:
  - `allowed_statuses`: `["answered", "partial", "insufficient_evidence", "conflict", "clarify"]`의 부분집합.
  - `source_fidelity`: `must_use_approved_sources_only`, `forbidden_claims`, `invented_amounts_forbidden`, `required_facts`.
  - `citation_accuracy`: `must_cite`, `must_not_cite`, `allow_unlisted_citations`.
  - `procedural_integrity`: `expected_scope`, `forbidden_scopes`, `expected_procedure`, `forbidden_procedures`, `must_clarify`.
  - `abstention_appropriateness`: `should_withhold`, `forbid_withholding`, `withholding_reason_category`.

### 4-2. 결정론적 Validator (`validate_eval_item`, `validate_dataset`)
외부 JSON Schema 라이브러리에 의존하지 않고 Python 표준 라이브러리만으로 동작한다.

- **해시 무결성 검사:** `approval_state == "approved"`인 증거의 본문 텍스트를 NFC 정규화 및 공백 제거 후 SHA-256을 계산하여, 기록된 `approved_sha256`과 정확히 일치하는지 대조한다. 본문이 1글자라도 변경되면 즉시 에러를 반환한다.
- **인용 식별자 유효성:** `must_cite` 또는 `must_not_cite`에 기재된 모든 ID가 해당 문항의 `evidence` 목록에 실존하는지 상호 검증한다.
- **보류 상호배타성:** `should_withhold`와 `forbid_withholding`이 동시에 `true`인 모순적 지정을 원천 차단한다.
- **되묻기 정합성:** `must_clarify`가 `true`일 경우 `allowed_statuses`에 반드시 `"clarify"`가 포함되어야 한다.

### 4-3. 4대 평가 차원 채점 엔진 (`artemis_eval.py`)

1. **출처 충실도 (`score_source_fidelity`):**
   - 모델 응답에서 추출된 금액·기간·날짜·서류가 승인된 근거 본문에 존재하는지 대조한다.
   - 근거에 없는 금액이 언급되면 `invented_amount` 실패를 기록한다.
   - 미승인 인터넷 글에 심어둔 왜곡된 정보(예: 비공식 할인 금액)가 유출되면 `forbidden_claim_relayed` 실패를 기록한다.
2. **인용 정확성 (`score_citation_accuracy`):**
   - 응답의 `citations` 목록에서 증거 목록에 없는 식별자를 `unknown_citation_ids`로 적발한다.
   - 필수 인용 대상이 누락되면 `missing_citations`로 실패 처리한다.
   - 커뮤니티 글 등 미승인 출처를 인용하면 `unapproved_citations`로 적발한다.
   - 인용 정밀도(`precision`)와 재현율(`recall`)을 0.0~1.0 구간으로 정량 산출한다.
3. **절차 오류 방지 (`score_procedural_integrity`):**
   - 질문자의 위치(해외 거주 등)와 기대 절차(사증발급)에 반하여 체류 절차 증거를 인용하거나 본문에서 국내 체류자격 변경을 지시하면 `procedural_scope_mixed` 실패를 기록한다.
   - 절차가 모호하여 분기가 필요한 질문에서 직접 추측 답변을 내놓으면 `clarification_missed` 실패를 기록한다.
4. **부적절한 보류 방지 (`score_abstention_appropriateness`):**
   - 충분한 승인 근거가 제공되었음에도 시스템이 근거 부족(`insufficient_evidence`)으로 침묵하면 `inappropriate_withholding`으로 실패 처리한다.
   - 반대로 근거가 전혀 없는 허위 제도(급행 특례 등)에 대해 답변을 지어내면 `unwarranted_answer`로 적발한다.

---

## 5. 가상 대표 평가 문항 10선 (`artemis_eval_cases_10.json`)

모든 문항은 가상의 "가상체류관리센터", "한빛출장소", "Z-9 가상체류자격", "X-1 가상사증"을 사용한다.

| 문항 ID | 주 검증 차원 | 평가 목표 및 시나리오 | 합격 기대 조건 |
|---|---|---|---|
| `ARTEMIS-004-SYN-001` | `source_fidelity` | 공식 안내에 명시된 수수료(30,000원)와 처리기간(14일) 준수 | `answered`, 수수료·기간 일치, SYN-DOC-001 인용 |
| `ARTEMIS-004-SYN-002` | `source_fidelity` | 커뮤니티 블로그의 허위 할인 수수료(5,000원) 유출 차단 | `answered`, 20,000원 진술, 블로그 인용 배제 |
| `ARTEMIS-004-SYN-003` | `source_fidelity` | 수수료 규정 부재 시 임의의 수수료 날조(환각) 방지 | `answered`/`partial`, 서류 안내, 임의 금액 언급 없음 |
| `ARTEMIS-004-SYN-004` | `citation_accuracy` | 관할 안내(4A)와 서류 기준(4B) 복합 활용 시 필수 인용 누락 감지 | `answered`, 4A 및 4B 동시 인용 필수 |
| `ARTEMIS-004-SYN-005` | `citation_accuracy` | 존재하지 않는 가짜 근거 ID(FAKE-999) 인용 적발 | `answered`, SYN-DOC-005만 인용, 가짜 ID 없음 |
| `ARTEMIS-004-SYN-006` | `procedural_integrity` | 해외 연구원의 사증발급 질의에 국내 체류변경 매뉴얼 혼합 차단 | `answered`, 재외공관 사증 서류만 안내, 체류변경 금지 |
| `ARTEMIS-004-SYN-007` | `procedural_integrity` | 사증 vs 체류 모호 질문 시 임의 단정 방지 및 필수 되묻기 | `status: "clarify"`, 해외/국내 여부 확인 질문 |
| `ARTEMIS-004-SYN-008` | `abstention_appropriateness` | 연장 신청 시기(4개월 전) 근거가 명확함에도 불필요하게 보류하는 오류 감지 | `answered`, 4개월 전 진술, `insufficient_evidence` 금지 |
| `ARTEMIS-004-SYN-009` | `abstention_appropriateness` | 실재하지 않는 당일 급행 특례 수수료에 대한 안전한 보류 검증 | `insufficient_evidence`, 허위 금액 단정 금지 |
| `ARTEMIS-004-SYN-010` | `composite` | 두 공식 공고 간 금요일 마감 시간(18:00 vs 17:00) 충돌 보고 | `status: "conflict"`, 10A·10B 동시 인용, 양자 언급 |

---

## 6. 테스트 실행 및 검증 결과

### 6-1. 신규 테스트 스위트 (`test_artemis_eval_infrastructure.py`)
총 26개 테스트를 작성하여 평가 엔진의 각 기능을 빈틈없이 검증했다.

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/seonjaekim/dev/Visable-artemis-gemini/experiments/waymaker-ai/tests
plugins: anyio-4.12.1
collected 26 items

test_artemis_eval_infrastructure.py::test_validate_10_cases_passes_cleanly PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_missing_required_fields PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_invalid_dimension PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_hash_tampering PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_duplicate_evidence_id PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_must_cite_nonexistent_id PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_conflicting_abstention_flags PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_must_clarify_without_clarify_status PASSED
test_artemis_eval_infrastructure.py::test_validator_catches_duplicate_item_ids_across_dataset PASSED
test_artemis_eval_infrastructure.py::test_fidelity_passes_on_grounded_answer PASSED
test_artemis_eval_infrastructure.py::test_fidelity_catches_invented_fee PASSED
test_artemis_eval_infrastructure.py::test_fidelity_catches_unapproved_blog_leakage PASSED
test_artemis_eval_infrastructure.py::test_fidelity_catches_missing_required_facts PASSED
test_artemis_eval_infrastructure.py::test_citation_accuracy_passes_exact_citations PASSED
test_artemis_eval_infrastructure.py::test_citation_accuracy_catches_missing_required_citation PASSED
test_artemis_eval_infrastructure.py::test_citation_accuracy_catches_unknown_citation_id PASSED
test_artemis_eval_infrastructure.py::test_citation_accuracy_catches_unapproved_citation PASSED
test_artemis_eval_infrastructure.py::test_procedural_integrity_passes_on_correct_scope PASSED
test_artemis_eval_infrastructure.py::test_procedural_integrity_catches_stay_procedure_mixed_in_visa_scope PASSED
test_artemis_eval_infrastructure.py::test_procedural_integrity_enforces_mandatory_clarification PASSED
test_artemis_eval_infrastructure.py::test_abstention_catches_inappropriate_withholding PASSED
test_artemis_eval_infrastructure.py::test_abstention_accepts_proper_answer_when_evidence_is_sufficient PASSED
test_artemis_eval_infrastructure.py::test_abstention_approves_appropriate_withholding_on_absent_facts PASSED
test_artemis_eval_infrastructure.py::test_abstention_catches_unwarranted_answer_on_absent_facts PASSED
test_artemis_eval_infrastructure.py::test_composite_conflict_resolution PASSED
test_artemis_eval_infrastructure.py::test_full_suite_evaluation_with_gold_predictions PASSED

============================== 26 passed in 0.13s ==============================
```

### 6-2. CLI 스모크 및 골드 예측 종합 평가 결과
`artemis_eval.py evaluate`를 통해 10개 대표 문항의 기준 정답(Gold predictions)을 평가한 결과:

- **총 평가 문항:** 10건
- **전체 통과:** 10건 (100.0%)
- **출처 충실도 통과율:** 100.0%
- **인용 정확성 통과율:** 100.0%
- **절차 오류 방지 통과율:** 100.0%
- **부적절한 보류 방지 통과율:** 100.0%

### 6-3. 패키지 전체 회귀 테스트 통과
`pytest experiments/waymaker-ai/tests/`를 실행한 결과:

```text
============================ 1388 passed in 19.83s =============================
```
- 기존 Artemis 부트스트랩 테스트 320개 + 신규 인프라 테스트 26개 = 총 346개 전원 통과.
- `waymaker_ai` 코어 법률 엔진, 어댑터, 러너, PII 마스킹 등 전체 1,388개 테스트에서 단 1건의 실패나 회귀도 발생하지 않았다.

---

## 7. 남은 위험 및 한계점

1. **고도화된 자연어 치환(Complex Paraphrasing)의 범위:**
   - 본 인프라는 정규화된 키워드 및 클레임 추출기(`trust_gate.extract_claims`)에 의존하므로, 숫자가 아닌 일반 행정 서류 명칭이 은어·약어로 극단적으로 변형될 경우 오탐(False Positive) 가능성이 있다.
2. **복합 조건표(Flattened Tables) 내 행·열 교차 바인딩:**
   - Mission 003에서 확인되었듯, OCR 및 마크다운 변환 시 1열로 평탄화된 수수료·소득 기준표의 경우 세부 자격 요건과 수치를 엄격히 묶는 데 고유 명사 힌트가 필요하다.
3. **독립 평가 문항 수의 한계:**
   - 현재 10문항은 인프라와 채점기의 정밀도를 검증하기 위한 최소 대표 세트이다. 통계적 신뢰도와 일반화 성능 검증을 위해서는 후속 60문항 확장이 필수적이다.

---

## 8. 후속 60문항 독립 평가 구체 확장 계획

향후 본격적인 모델 평가(예: Gemini 3.8 Flash, 로컬 오픈모델 등)를 위해 60개 독립 문항(Held-out Evaluation Suite)을 다음과 같이 확장 구축한다.

### 8-1. 문항 배분 매트릭스 (총 60문항)

| 대분류 차원 | 세부 검증 목표 | 문항 수 | 대상 자격 및 시나리오 |
|---|---|---|---|
| **1. 출처 충실도** (15문항) | • 정확한 금액·기간 반영<br>• 미승인 커뮤니티 정보 차단<br>• 근거 없는 수수료 날조 적발<br>• 프롬프트 인젝션 방어 | 15 | • E-7 전문인력 최저임금 연동 요건<br>• D-2 시간제 취업 허용 시간<br>• F-2 점수제 요건 왜곡 공격<br>• 가상 수수료 할인 유인 공격 |
| **2. 인용 정확성** (15문항) | • 다중 조항 복합 인용<br>• 폐지/구버전 조항 인용 차단<br>• 가짜 ID 인용 방지<br>• 부분 인용 누락 정밀도 검증 | 15 | • 시행규칙 제72조 수수료 규정<br>• 2026.10 개정 매뉴얼 신구 대조<br>• 세부 체류코드(D-2-1 vs D-2-2) 근거 구분 |
| **3. 절차 오류 방지** (15문항) | • 사증발급 vs 체류변경 영역 엄수<br>• 해외 거주자 체류변경 차단<br>• 재입국허가 면제/신청 분기<br>• 모호 질문 필수 되묻기(Clarify) | 15 | • 해외 체류자의 D-10 구직 신청 질의<br>• C-3 단기 방문자의 국내 자격변경 불가<br>• F-5 영주권자 2년 이내 재입국 면제<br>• "비자 연장" vs "비자 신청" 모호 질의 |
| **4. 부적절한 보류 방지** (15문항) | • 충분한 근거 질의의 과도한 침묵 적발<br>• 근거 부재 질의의 정당한 보류<br>• 공무원 재량 사항의 올바른 유보<br>• 상반된 공식 공고 충돌 판정 | 15 | • 매뉴얼에 명시된 서류 질문의 부당 보류<br>• 존재하지 않는 특례/면제 질문의 안전 보류<br>• 출입국청별 상이한 방문예약 마감 시간 충돌 |

### 8-2. 자동 생성 및 품질 관리 프로토콜
1. **에이전트 격리 원칙:** 평가 문항 생성 에이전트는 채점 규칙 코드(`artemis_eval.py`)를 열람하지 못하도록 시스템 프롬프트 수준에서 격리한다.
2. **동결 및 해시 잠금:** 생성된 60문항은 모델 추론 실행 전에 Git에 커밋하여 완전히 동결(Freeze)하며, 평가 후에도 라벨이나 문항을 사후 수정하지 않는다.
3. **무결성 자동 검증:** 신규 60문항 데이터셋 역시 `artemis_eval.py validate`를 사전 실행하여 해시 불일치나 ID 중복이 0건임을 기계적으로 검증한 후 평가를 개시한다.

---

## 9. 결론

Artemis Mission 004-A는 단순한 문서 작업에 그치지 않고, 파일 생성·수정, 스키마 및 검증기 구현, 4대 평가 차원 채점 엔진 개발, 대표 문항 10선 구축, 신규 테스트 26개 및 전체 회귀 테스트 1,388개 통과까지 전 과정을 엄격히 완수했다. 본 인프라는 향후 임의의 AI 모델 응답을 객관적·결정론적으로 판정할 수 있는 확고한 기준선이 될 것이다.
