# 독립 법률 검토 양식 (Mission 005-F)

출입국·체류 법령과 행정 절차에 자격이 있는 검토자를 위한 양식입니다. 검토 대상 묶음은
`runs/mission005f/review_packet.json`(DEV-20 20건, 005-E 계약 v2 응답)이고, 만든 도구는 `legal_review_packet.py`입니다.

이 양식은 벤치마크 정답을 바꾸지 않습니다. 후보 정답이 확정 정답(gold)이 되려면, 권한 있는 검토가 이 묶음에 기록되고
그 결과가 **별도 버전의 데이터셋**으로 나와야 합니다. 그 전까지 독립 법률 검토 상태는 `not_verified`입니다.

## 1. 항목마다 볼 것

묶음의 각 항목에는 질문, 근거 원문과 출처 정보, 기록된 모델 응답, 현재 후보 정답, 채점기 판정, 분석자가 남긴 열린 질문이 있습니다.
분석자 메모는 의견입니다. 검토자가 따를 필요가 없습니다.

## 2. 점검 목록

각 질문에 `yes`, `no`, `uncertain` 중 하나를 적습니다. 비워 두면 `null`(아직 판단 안 함)입니다.

| 필드 | 묻는 것 |
|---|---|
| `source_authentic` | 인용된 규정·매뉴얼이 실제로 그 기관이 낸 문서인가 |
| `effective_at_relevant_time` | 질문 시점에 시행 중이었는가 |
| `applies_to_subject_and_procedure` | 질문의 대상(체류자격·사람)과 절차(사증·체류)에 적용되는가 |
| `response_preserves_legal_meaning` | 모델 응답이 근거의 법적 의미를 바꾸지 않았는가 |
| `required_facts_necessary` | 후보 정답의 필수 사실마다, 정말 빠지면 안 되는가 |
| `candidate_expected_answer_valid` | 후보 정답 자체가 맞는가 |
| `source_trust_rules_appropriate` | 공식·비공식 출처를 가르는 규칙이 이 항목에 맞는가 |
| `evaluator_classification_justified` | 채점기의 실패 분류가 타당한가 |

판단 이유는 `reasoning`에, 뒷받침하는 법령·고시·판례는 `legal_authority`에 적습니다(조문, 링크, 확인한 날짜).

## 3. 판단 상태

| 상태 | 뜻 |
|---|---|
| `not_reviewed` | 아직 아무도 보지 않음(초기값) |
| `in_review` | 검토 중 |
| `agree` | 후보 정답과 채점기 판정에 동의 |
| `disagree` | 동의하지 않음. 법적 근거 필수 |
| `needs_more_information` | 근거 원문이나 시행 시점 확인이 더 필요 |
| `escalated` | 정책 판단이나 상급 검토가 필요 |

`not_reviewed`가 아닌 상태에는 검토자 이름·자격·소속, 검토 일시, 감사 기록이 있어야 합니다. `agree`와 `disagree`에는 이유가 있어야 합니다.

## 4. 이견 처리

두 번째 검토자가 있으면 `second_review`에 같은 형식으로 적습니다. 두 상태가 다르면 `disagreement`에
각자의 입장, 논의 내용, 최종 결론과 그 결론을 낸 사람을 적습니다. 이견을 지우거나 덮어쓰지 않습니다.

## 5. 버전과 감사 기록

- 묶음에는 만든 커밋, 데이터셋 SHA-256, 응답 파일 SHA-256이 들어 있습니다. 검토는 그 버전에 대한 판단입니다.
- 상태가 바뀔 때마다 `audit_trail`에 `at`, `actor`, `action`, `from_state`, `to_state`, `note`를 한 줄 더합니다. 이전 줄은 고치지 않습니다.
- 검토가 끝나면 `python3 artemis_bootstrap/legal_review_packet.py validate <묶음 경로>`로 형식을 확인합니다.
- 검토 결과를 반영한 정답은 새 파일·새 버전으로 냅니다. 기존 DEV-20 파일(`artemis_eval_dev_20.json`)은 바꾸지 않습니다.
