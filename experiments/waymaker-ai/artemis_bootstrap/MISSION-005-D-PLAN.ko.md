# Mission 005-D 준비: 개발 후보 20건 실제 CUDA 추론 계획

작성일 2026-10-30. 이 문서는 계획입니다. 20건 평가는 아직 실행하지 않았습니다.

## 전제

- 저장소 CUDA 러너가 무료 Colab T4에서 공식 E4B를 실제로 올리고 합성 3건을 생성했습니다
  ([Mission 005-C.2 기록](runs/mission005c2-cuda/MISSION-005-C2-REPORT.ko.md)).
- 대상은 [benchmarks/artemis_eval_dev_20.json](benchmarks/artemis_eval_dev_20.json)의 20건이며 모두 `dev_candidate`입니다.
  독립 법률 검토를 거치지 않았으므로 결과는 **후보 진단 수치**입니다. Official Gold Accuracy는 `N/A`로 둡니다.
- held-out 40건은 저장소에 정답이 함께 있어 `isolation_not_verified`입니다. 이번 계획에서 실행하지 않고, 독립 미공개 평가로 부르지 않습니다.

## 실행 방법

1. 재현 노트북으로 같은 방식의 런타임을 준비합니다(무료 T4 확인, 코드 SHA 고정, 패키지 고정, 체크포인트 SHA-256).
2. 같은 Python 프로세스에서 모델을 **한 번만** 올리고 20건을 이어서 돌립니다.

   ```python
   import gemma4_cuda_runtime as cuda, artemis_runner as runner
   prepared = cuda.PreparedRun(); prepared.prepare()
   adapter = runner.CudaTransformersAdapter(max_tokens=256, prepared=prepared)
   summary = runner.ArtemisEvaluationRunner(
       adapter=adapter, mode=runner.EvaluationMode.CANDIDATE_EVAL,
       benchmark_path='artemis_bootstrap/benchmarks/artemis_eval_dev_20.json',
       out_dir='/content/artemis_dev20_<시각>').run()
   ```

   어댑터가 문항을 `inference_input`으로 투영하므로 정답·채점 기준은 프롬프트에 들어가지 않습니다.
3. 산출물 `run_summary.json`, `report.md`, `error_summary.csv`, `run_manifest.json`을 고치지 않고 저장소 `runs/` 아래에 둡니다.
   005-C.2처럼 SHA-256으로 전달 경로를 확인합니다.
4. 실행이 끝나면 런타임을 연결 해제·삭제합니다.

## 무료 GPU 사용량

- 이번 측정 기준 로딩 약 70초, 합성 사례당 4~9초(입력 126~200토큰). 개발 후보는 근거가 길어(문항당 근거 JSON 최대 약 1,300자)
  사례당 시간이 더 걸릴 수 있습니다. 20건 전체 예상치는 측정값이 아니라 추정이며, 실행 기록의 실제 값을 씁니다.
- 체크포인트는 런타임마다 한 번 받습니다(약 2분). 20건은 한 세션에서 끝냅니다.
- 메모리 부족이나 런타임 종료가 나면 한 번만 다시 시도합니다. 다시 실패하면 멈추고 실패 기록을 남깁니다.

## 평가 축

평가기는 이미 있는 [artemis_eval.py](artemis_eval.py) 차원을 그대로 씁니다. 새 채점 기준을 만들지 않습니다.

| 요청 축 | 평가기 차원·실패 코드 |
|---|---|
| 답변 정확도 | `source_fidelity`, `required_fact_missing`, `invented_amount`, `polarity_flipped`, `permission_flipped` |
| 인용 정확도 | `citation_accuracy` (`missing_citations`, `unlisted_citations`, 알 수 없는 ID) |
| 근거 충실도 | `source_fidelity`, `unsupported_claim`, `subject_binding_mismatch`, `role_mismatched` |
| 유보 적절성 | `abstention_appropriateness`, `must_clarify_not_performed` |
| 절차 구분 | `procedural_integrity` (`procedural_error`, `scope_mismatch`) |

- 응답 계약을 통과하지 못한 출력(`generated_but_invalid`)은 실패로 셉니다. 인용 없이 답한 경우도 계약에서 거절됩니다.
- 근거 없는 법률 답변을 성능 성공으로 세지 않습니다.

## 오류 유형 분석

- 러너의 `diagnostic_disagreements`와 `error_summary.csv`로 실패 코드를 셉니다.
- 사례별로 원본 출력, 종료 이유(`eos`/`length`), 생성 토큰 수를 같이 봅니다. `length` 종료는 토큰 한도 문제로 따로 분류합니다.
- 상태 선택 경향(예: 005-C.2에서 답할 수 있는 질문에 `partial`을 고른 것)을 별도로 집계합니다.

## 후보 평가와 공식 Gold 평가의 구분

- 이번 결과는 `candidate_eval` 모드, `is_official_gold: false`입니다.
- MLX 결과, mock, 녹화 응답과 합산하지 않습니다(`transformers_cuda` 집계 키).
- 독립 검토자가 연결되기 전에는 어떤 문항도 gold로 승격하지 않습니다.

## QLoRA 학습 필요성 판단 기준 (제안)

20건만으로 학습 여부를 결정하지 않습니다. 다음은 다음 단계에서 판단할 때 볼 신호입니다.

- 응답 계약 실패가 반복된다: 프롬프트·디코딩 조정을 먼저 시도합니다. 학습 근거로는 약합니다.
- 인용 누락·목록 밖 인용이 근거가 충분한 문항에서 반복된다: 학습 후보 신호입니다.
- 유보해야 할 문항에서 답하거나, 답할 문항에서 지나치게 유보한다: 학습 후보 신호입니다.
- 절차 혼동(사증과 체류)이 반복된다: 근거 검색·라우팅 문제인지 먼저 가립니다.
- 어떤 경우든 학습 데이터는 독립 검토를 거친 자료만 씁니다. 후보 정답을 학습 정답으로 쓰지 않습니다.

## 하지 않는 것

held-out 40건 실행, gold 승인, 법률 정확도 주장, 유료 GPU, 20건 자동 반복 실행.
