# ARTEMIS MISSION 004-C 실행 보고서
## 모델 평가 런타임, 사람 법률 검토 거버넌스 및 재현 가능 벤치마킹 체계

- **보고서 버전**: 1.1.0 (Mission 004-C 독립 코드 리뷰 시정 반영)
- **작성 일자**: 2026-10-29
- **수행 환경**: `club-paradiso/Visable` (`feat/artemis-mission004-c`)
- **기반 커밋**: `a37ebc1` (PR #723 `main` 병합 커밋)
- **책임 에이전트**: Artemis Evaluation Subsystem (Gemini 3.8 Flash)

---

## 1. 미션 개요 및 핵심 목표

Mission 004-A(평가 인프라 기본 수립), Mission 004-B(60문항 후보군 구축) 및 Mission 004-B.1(독립 코드 리뷰 시정)을 통해 정립된 채점 및 검증 규칙을 바탕으로, Mission 004-C에서는 **실제 모델 평가를 수행하고 사람 법률 검토 절차를 체계적으로 추적하는 실행 및 거버넌스 계층**을 구축하였습니다.

독립된 임시 프로토타입을 만들지 않고 기존 Artemis 및 Waymaker AI 계약을 확장하여 다음 핵심 기능을 완성하였습니다.

1. **오프라인 모델 평가 런타임 (`artemis_runner.py`)**: 결정론적 Mock, 사전 기록 응답(Recorded), 로컬 MLX 어댑터를 아우르는 통합 실행기.
2. **3단계 평가 모드 엄격 격리**:
   - Mode A (인프라 검증): 가상 합성 픽스처(10문항) 기반 소프트웨어 기능 및 회귀 검증.
   - Mode B (후보군 평가): 개발(20문항) 및 홀드아웃(40문항) 후보군에 대한 탐색적 진단 평가. 미검증 법률 문항 격리.
   - Mode C (공식 골드 평가): 독립적인 사람 법률 전문가 서명이 완료된 문항에 대해서만 공식 지표 산출. 미검증 시 `N/A` 표기.
3. **사람 법률 검토 거버넌스 원장 프로토타입 (`legal_review_governance.py`)**:
   - `unreviewed` → `in_review` → `verified_by_human` / `rejected` / `needs_revision` / `superseded` 엄격 상태 전이 머신.
   - 로컬 비권위적(non-authoritative) 추적 원장으로서의 성격 명시.
   - 호출자 전달 불리언 플래그(`is_human=True`)나 임의 이름 문자열을 인증된 사람 승인으로 신뢰하지 않음.
   - 외부 공인 전자서명(PKI/OAuth) 연동 전까지 공식 골드 승격 차단 (`AuthoritativeGoldPromotionDisabledError`, Fail-Closed).
   - 공식 증거 스냅샷 의무화 (질의응답 대체 금지) 및 사후 증거 변조 감지 (`ReviewIntegrityError`).
4. **정밀 오류 진단 분류 체계 (Diagnostic Taxonomy)**: 14개 범주의 오류 분류 및 불일치 진단 집계.
5. **재현 가능 실행 아티팩트 자동 생성**: `run_summary.json`, `report.md`, `error_summary.csv`, `run_manifest.json`.

---

## 2. 모델 평가 런타임 아키텍처 및 어댑터

### 2.1 지원 어댑터 인터페이스 (`BaseModelAdapter`)

- **MockModelAdapter**:
  - 회귀 시험과 캘리브레이션을 위한 결정론적 Mock 어댑터입니다.
  - 사전 정의 프리셋(`gold`, `wrong_facts`, `polarity_flip`, `swap_table`, `unlisted_citation`, `improper_withhold`, `injection_vulnerable`, `timeout`, `custom`)을 지원합니다.
- **RecordedResponseAdapter**:
  - 모델의 오프라인 생성 결과를 기록한 JSON 및 JSONL 파일을 로드하여 평가합니다.
  - 누락된 문항이나 비정형 응답에 대한 예외 처리를 내장하였습니다.
- **LocalModelAdapter**:
  - Apple Silicon M1 (8GB RAM) 환경 제약을 준수하는 오프라인 MLX 로컬 모델 어댑터입니다.
  - 로컬 캐시 디스크 여유 공간(최소 5GB)과 오프라인 가중치 존재 여부를 사전 확인합니다.
  - 가중치가 없거나 의존 패키지가 부재할 경우 실행 상태를 `not_executed`로 정상 기록하며 가상 추론 결과를 조작하지 않습니다.

### 2.2 3단계 평가 모드 격리 규칙

```
+---------------------------------------------------------------------------------+
| Mode A: 인프라 검증 (infra_validation)                                           |
| - 대상: artemis_eval_cases_10.json (가상 합성 데이터 10문항)                      |
| - 목적: 채점기 규칙 및 파서 회귀 테스트 (법률 정확도 지표 미산출)                |
+---------------------------------------------------------------------------------+
| Mode B: 후보군 평가 (candidate_eval)                                            |
| - 대상: dev_20, heldout_40, candidates_60 (후보 60문항)                         |
| - 목적: 모델 행동 양식 및 진단 루브릭 일치율 탐색 (candidate_evaluation_only)    |
| - 거버넌스: official_gold_pass_rate = None (공식 골드 정확도 미산출, N/A 표기)  |
+---------------------------------------------------------------------------------+
| Mode C: 공식 골드 평가 (gold_eval)                                              |
| - 대상: legal_review_governance를 통해 verified_by_human 서명 완료된 문항만 필터 |
| - 거버넌스: 서명 완료 문항이 0건인 경우 pass_rate = None (N/A 표기)             |
+---------------------------------------------------------------------------------+
```

---

## 3. 사람 법률 검토 거버넌스 및 무결성 보안 체계

### 3.1 상태 전이 머신 (Review State Machine)

```
 [ unreviewed ] (초기 상태: 60문항 전수)
       |
       v (claim_for_review: 검토자 배정, 로컬 기록)
  [ in_review ]
       |---> [ verified_by_human ] (approve: 실질 사유 및 공식 증거 원문 스냅샷 필수)
       |            |
       |            +---> [ superseded ] (지침 개정 등으로 대체 시)
       |---> [ rejected ] (reject: 사유 필수)
       +---> [ needs_revision ] (request_revision: 수정 요청 사유 필수)
```

### 3.2 핵심 거버넌스 원칙 및 독립 리뷰 시정 조치

1. **로컬 비권위적 프로토타입 성격 명시**:
   - `legal_review_governance.py`는 로컬 리뷰 진행 상황을 기록하는 감사 원장 프로토타입입니다.
   - 호출자가 전달하는 `is_human=True` 불리언 값과 `reviewer_id` 문자열은 자체 주장(self-asserted)에 불과하며, 암호학적 신원 인증이나 법률 전문가 인가 서명으로 취급하지 않습니다.
   - 단순 문자열 부분 매칭(`is_ai_identifier`)은 기본적인 봇 명칭 필터일 뿐, 자동화 에이전트의 사람 사칭을 원천 차단하는 절대적 방어책이 아님을 문서와 예외 처리에 명시하였습니다.
2. **공식 증거 스냅샷 의무화 및 대체 금지**:
   - 승인 판정(`record_decision(APPROVE)`) 시 반드시 공식 출처 원문 텍스트(`evidence_snapshot_text`)를 제공해야 합니다.
   - 질문이나 답변 텍스트로 증거 스냅샷을 유추하거나 대체하는 기존 취약 로직을 전면 제거하였습니다.
   - 제공된 스냅샷 텍스트는 원장에 등록된 공공기관 지침/법령 발췌문과 일치해야 하며, 불일치 시 `ReviewIntegrityError`로 즉시 거부됩니다.
3. **증거 위변조 감지 및 출처 해시 검증 (`validate_item_evidence_integrity`)**:
   - 검토 완료 후 문항의 증거 텍스트가 사후 수정되거나 변조된 경우, 스냅샷 해시와 현재 문항 증거 해시의 불일치를 감지하여 즉시 차단합니다.
   - 출처 메타데이터의 `content_sha256`이 증거 본문 해시와 상충하는 경우에도 검증을 실패시킵니다.
4. **공식 골드 승격의 Fail-Closed 원천 비활성화 (`AuthoritativeGoldPromotionDisabledError`)**:
   - 본 로컬 프로토타입 환경에는 독립된 공인인증(PKI) 또는 외부 IAM/OAuth 기반 법률 대리인 전자서명 검증 서비스가 연결되어 있지 않습니다.
   - 따라서 로컬 원장의 승인 기록만으로는 공식 골드(`official_gold`)로 승격될 수 없으며, `promote_to_gold` 호출 시 `AuthoritativeGoldPromotionDisabledError`를 발생시켜 안전하게 차단(Fail-Closed)합니다.
   - 소프트웨어 테스트만으로 60개 후보 문항 중 어느 것도 공식 검증 골드로 임의 승격할 수 없습니다.

---

## 4. 진단 오류 분석 체계 (Diagnostic Taxonomy)

채점 결과의 실패 원인을 세분화하여 진단 불일치 건수를 유형별로 자동 집계합니다.

| 오류 분류 코드 | 분류 명칭 | 감지 기법 |
|:---|:---|:---|
| `polarity_flipped` | 부정 및 금지 표현 반전 | `detect_polarity_and_permission_reversal` 교차 어휘 검증 |
| `permission_flipped` | 허가 요건 반전 | 긍정 및 부정 조동사 매칭 |
| `role_mismatched` | 표 역할 및 컬럼 전치 | `detect_role_and_column_swaps` 한도 수치 교환 감지 |
| `subject_binding_mismatch` | 주체-수치 오속성 결합 | `check_forbidden_subject_binding` 절 분해 및 극성 가드 |
| `missing_citations` | 필수 근거 인용 누락 | `set(must_cite) - set(citations)` 집합 검증 |
| `unlisted_citations` | 미승인 출처 인용 | `citations - set(must_cite)` 미인가 출처 차단 |
| `invented_amount` | 미근거 수치 날조 | 출처 외 금액 및 기간 정규식 검증 |
| `unsupported_claim` | 금지 및 미승인 주장 진술 | `forbidden_claims` 부분 문자열 매칭 |
| `scope_mismatch` | 절차 영역 혼동 | 사증발급(해외)과 체류절차(국내) 도메인 교차 감지 |
| `must_clarify_not_performed` | 되묻기 미수행 | 모호한 질의에서 clarify 상태 누락 감지 |
| `inappropriate_withholding` | 부적절한 과도 보류 | 충분한 근거가 있음에도 보류한 경우 감지 |
| `prompt_injection_vulnerable` | 프롬프트 인젝션 취약 | 적대적 지시 복종 및 시스템 지침 유출 감지 |
| `inference_timeout` | 추론 타임아웃 | 어댑터 실행 시간 초과 감지 |
| `parse_error` | 응답 파싱 오류 | JSON 규격 미준수 및 상태값 오류 감지 |

---

## 5. 자동 검증 및 테스트 결과

### 5.1 Artemis 전용 테스트 실행 결과 (98/98 Passed)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_infrastructure.py \
       experiments/waymaker-ai/tests/test_artemis_eval_reliability.py \
       experiments/waymaker-ai/tests/test_artemis_eval_benchmark_60.py \
       experiments/waymaker-ai/tests/test_artemis_runner.py \
       experiments/waymaker-ai/tests/test_artemis_legal_governance.py \
       experiments/waymaker-ai/tests/test_artemis_error_analysis.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/seonjaekim/dev/Visable-artemis-gemini
plugins: anyio-4.12.1
collected 98 items

experiments/waymaker-ai/tests/test_artemis_eval_infrastructure.py ...... [  6%]
............................                                             [ 34%]
experiments/waymaker-ai/tests/test_artemis_eval_reliability.py ......... [ 43%]
...........                                                              [ 55%]
experiments/waymaker-ai/tests/test_artemis_eval_benchmark_60.py ......   [ 61%]
experiments/waymaker-ai/tests/test_artemis_runner.py .............       [ 74%]
experiments/waymaker-ai/tests/test_artemis_legal_governance.py ......... [ 83%]
.........                                                                [ 92%]
experiments/waymaker-ai/tests/test_artemis_error_analysis.py .......     [100%]

============================== 98 passed in 0.41s ==============================
```

### 5.2 한국어 품질 검사 (`kolint`)

```bash
node ~/dev/korean-language-quality/bin/kolint.mjs --genre documentation \
     experiments/waymaker-ai/artemis_bootstrap/MISSION-004-C-REPORT.ko.md \
     experiments/waymaker-ai/artemis_bootstrap/reviews/legal_review_ledger_report.md
```

```text
kolint: 0 unit(s) with findings, 0 blocking (S1, non-advisory).
kolint: 0 unit(s) with findings, 0 blocking (S1, non-advisory).
```

---

## 6. 결론 및 제약 사항

1. **실제 가중치 추론 미실행 (`not_executed`) 명시**:
   - Gemma 4 MLX 가중치는 4GB 이상의 저장 공간과 수 분의 로딩 시간이 소요됩니다. MacBook Air M1 (8GB RAM) 환경 제약 및 엄격 지침(대규모 모델 다운로드 및 유료 API 사용 금지)에 따라 로컬 가중치 추론은 실행하지 않았습니다.
   - `LocalModelAdapter`는 가중치 부재 시 상태를 `not_executed`로 정상 기록하며 허위 점수를 일절 생성하지 않았습니다.
2. **독립 법률 검토 대기 유지 및 0건 골드 보증**:
   - 60개 벤치마크 후보 문항은 현재 전수 `unreviewed` 상태로 원장에 등재되어 있습니다.
   - 외부 공인 법률 전문가(출입국 전문 행정사 및 변호사)의 실제 독립 전자서명이 완료될 때까지 공식 골드 정확도는 `N/A`로 유지되며, 소프트웨어 테스트나 로컬 프로토타입 플래그를 통한 자동 승격은 전면 차단되었습니다.
