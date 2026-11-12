# Mission 005-G 구조 감사와 신뢰 근거 처리 설계

행동 명세는 `trusted_evidence_spec.md`에 있습니다. 이 문서는 바꾸기 전에 무엇이 빠져 있었는지와 무엇을 어디에 넣었는지를 적습니다.
모든 새 경로는 연구용입니다. 운영 백엔드(`backend/`)에는 연결하지 않았습니다.

## 1. 감사: 바꾸기 전의 경로

```
근거 수집 → (출처 검증 없음) → 근거 선택(전부) → 프롬프트 구성 → E4B 생성 → 응답 계약 검사 → (평가기만) 신뢰 판정 → 공개
```

| 단계 | 파일 | 신뢰 판단 | 문제 |
|---|---|---|---|
| 근거 투영 | `waymaker_ai/inference_input.py` | `source.provenance`를 허용 값 3개로만 걸러 모델에 넘김 | 값은 문서 자신이 붙인 것입니다. 위조 문서가 `official_manual`이라고 적으면 모델에게 공식으로 보입니다 |
| 실험 게이트 | `artemis_bootstrap/trust_gate.py` `is_trusted` | 문서의 `source.approval_state == "approved"` | 승인 표시도 문서에 딸린 필드입니다. 무결성 검사(`approved_sha256`)도 같은 문서의 필드와 비교하므로 둘 다 고치면 통과합니다 |
| CUDA 실행 | `run_dev20_cuda.py`, `synthetic_safety_gate.py` | 없음. 근거를 모두 모델에 넘김 | 신뢰는 생성이 끝난 뒤 평가기 쪽 `trust` 기록으로만 판정됐습니다. 사용자에게 나갈 답을 막는 장치가 아니었습니다 |
| 평가 | `synthetic_safety_gate.py` | 사례의 `trust` 기록 | 평가 전용 정보라 운영에서는 쓸 수 없습니다 |

모델이 보는 정보와 평가기만 아는 정보가 달랐습니다. 모델은 문서가 스스로 주장하는 출처 종류만 봤고, 진짜 신뢰 판정은 평가기 쪽에만 있었습니다.
005-F의 치명 실패 4건(A05F-10·12·34·42)은 모두 이 틈에서 나왔습니다. 모델에게 "출처 없는 글은 쓰지 말라"고 적었지만 그 판단을 모델에게 맡긴 셈이었습니다.

검증되지 않은 글이 인정 근거처럼 보이게 되는 지점은 셋이었습니다.
1. 문서의 `provenance` 값이 그대로 모델 입력이 됨.
2. 문서의 `approval_state`·`approved_sha256`가 그대로 신뢰 판정이 됨(실험 경로).
3. 근거 선택 단계 자체가 없어, 다른 하위 코드·관할·절차·시기의 근거가 모두 모델에 감.

## 2. 설계: 바꾼 뒤의 경로

```
근거 수집
 → evidence_registry       신뢰 기록부 조회 (문서 자기 주장은 쓰지 않음, 없으면 미검증)
 → evidence_admissibility  기록부·무결성·권위·승인·관할·체류자격·절차·위치·시행일·대체 관계 순서 판정
 → 추론 전 판단            proceed | system_withheld | system_clarification | review_required
 → (proceed만) E4B 생성     채택 근거 + reply_language + uncovered_items, 계약 v4
 → grounding_guard         release | withhold | review_required | invalid_response
 → 공개 응답               출처 표시: model_generated / system_* / post_generation_blocked / review_required / invalid_response
```

| 층 | 파일 | 역할 |
|---|---|---|
| 신뢰 기록부 | `waymaker_ai/evidence_registry.py` | 기록 형식 검사, 합성 기록부와 실제 기록부 분리(합성 기록은 실제 근거를 보증할 수 없음), 읽기 실패 시 닫힌 쪽 실패 |
| 근거 채택 | `waymaker_ai/evidence_admissibility.py` | 질문 맥락(사용자 입력 + 질문 글), 문서별 결정과 사유, 요청 항목, 추론 전 판단 |
| 응답 계약 v4 | `waymaker_ai/response_contract.py` | 모델은 진위를 판단하지 않음. 시스템이 정한 답 언어와 미포함 항목을 받음 |
| 모델 입력 | `waymaker_ai/inference_input.py`, `artemis_bootstrap/gemma4_runtime.py` | `system` 필드는 허용 목록(`reply_language`, `uncovered_items`)만, v4에서만 사용. v1~v3 입력은 그대로 |
| 응답 검사 | `artemis_bootstrap/grounding_guard.py` | 계약·인용·값·허가/금지·의무·체류자격 코드·언어·미포함 항목 검사, 시스템 대체 응답 |
| 평가 게이트 v2 | `artemis_bootstrap/synthetic_safety_gate_v2.py` | 추론 전·원 모델·끝단 세 갈래를 따로 채점, 005-F 원 모델 문턱 유지 + 끝단 문턱 추가 |

## 3. 판단 원칙

- **권위는 스스로 선언할 수 없습니다.** 문서 본문과 `source` 필드는 신뢰 판단에 쓰지 않습니다.
- **SHA-256은 바이트 일치만 보입니다.** 기록부에 적힌 내용과 같다는 뜻이지, 법적 권위의 증명이 아닙니다.
- **모르면 막습니다.** 기록부가 없거나, 기록이 형식에 맞지 않거나, 시행일·관할·상위 코드 적용 범위를 알 수 없으면 채택하지 않습니다.
- **코드 이름으로 위계를 짐작하지 않습니다.** `Y-9`가 `Y-9-1`을 덮는다는 것은 기록부의 `all_subcategories_of`로 검증된 경우에만 인정합니다.
- **과거 규칙도 근거가 될 수 있습니다.** 질문 기준일에 시행 중이었으면 채택합니다. 기준일은 사용자 입력, 질문 속 날짜, 평가 기준일 순서로 정합니다.
- **시스템 보류는 모델 성공이 아닙니다.** 원 모델 성적과 끝단 공개 결과를 따로 기록합니다.
- **차단만 하는 시스템은 통과하지 못합니다.** 게이트 v2는 근거 있는 답의 공개율(가용성) 하한을 둡니다.

## 4. 합성과 실제의 분리

| | 합성 연구 | 실제 운영 |
|---|---|---|
| 기록부 출처 | 평가 집합과 함께 동결된 기록(`verification.method = synthetic_fixture`) | 독립적으로 관리되는 출처 기록부 또는 권한 있는 검토(`registry_lookup`, `authorized_review`) |
| 현재 상태 | 개발 28건, 잠긴 수용 63건 | **기록부 없음.** `artemis_bootstrap/registry/real_world_registry.json`이 없으므로 닫힌 쪽으로 실패 |
| 서로 섞임 | 합성 기록은 실제 기록부에서 무시됨 | DEV-20의 평가 전용 승인 상태는 기록부로 쓰지 않음 |

따라서 이번 구조로 DEV-20을 돌리면 근거가 모두 미검증이어서 시스템이 보류합니다. 이것은 정확도 측정이 아니라 실제 신뢰 규칙 아래의 가용성입니다.

## 5. 바꾸지 않은 것

- 005-F 게이트(`synthetic_safety_gate.py`), `trust_gate.py`, `language_compliance.py`, `claim_support_validation.py`는 고치지 않았습니다. 005-F 판정을 그대로 재현하기 위해서입니다.
- `response_contract.py`, `inference_input.py`, `gemma4_runtime.py`는 v4 때문에 바뀌었습니다. 005-F 매니페스트에 고정된 해시는 005-F 고정 커밋의 파일과 같음을 테스트로 확인하고,
  005-F 판정은 그 커밋의 코드를 git에서 꺼내 바이트 단위로 재현합니다.
- 운영 백엔드, 모델 가중치, 체크포인트 검증, NF4 검증은 건드리지 않았습니다.
