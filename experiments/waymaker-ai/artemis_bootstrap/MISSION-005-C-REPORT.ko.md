# Mission 005-C 보고서: Colab CUDA 추론 통합과 재현성

작성일 2026-10-30. 브랜치 `feat/artemis-cuda-colab-inference`, PR #726 head
`d9a079dc9347b5b6670e316fda275cc4a6cf4483`에서 갈라졌습니다.

> **2026-10-30 갱신 (Mission 005-C.1)**: 이 보고서는 005-C 작업 당시 상태입니다. 그 뒤 브랜치를 푸시했고
> PR #730(Draft)이 열렸습니다. #730의 base는 PR #726 브랜치 `feat/artemis-mission005-a`로 바꿨습니다.
> 실행 기록 검증 강화, 노트북 고정, 현재 상태는 [Mission 005-C.1 보고서](MISSION-005-C1-REPORT.ko.md)를 보세요.
> 새 CUDA 코드는 아직 실제 GPU에서 실행되지 않았습니다(`not_executed`).

## 요약

- Colab T4 실행 기록 7개 수치는 내려받은 노트북의 저장된 출력과 모두 일치합니다.
  다만 노트북을 다시 실행해 확인한 것은 아니므로 **독립 검증 완료가 아닙니다**.
  ([감사 보고서](COLAB-T4-RUN-AUDIT.ko.md))
- 공식 E4B 체크포인트용 CUDA 실행 경로를 MLX 경로와 따로 만들었습니다. MLX 코드는 그대로 둡니다.
- 이 맥에는 CUDA GPU가 없어 실제 CUDA 생성은 **실행하지 않았습니다**. 이 맥에서 돌린 사전 검사는
  `not_executed`(종료 코드 3)입니다.
- 회귀 검사: 기존 1,561건과 새 46건, 합계 1,607건 통과. CI의 나머지 오프라인 단계도 모두 통과했습니다.
- 기존 MLX 실행 상태 `not_executed`, Official Gold Accuracy `N/A`는 바뀌지 않습니다.

## 1. 저장소와 PR #726 상태

| 항목 | 값 |
|---|---|
| PR | #726, Draft, `feat/artemis-mission005-a` → `main` |
| head | `d9a079d` (요청서의 커밋과 같음) |
| main 대비 | main보다 3커밋 뒤, 4커밋 앞 |
| 변경 범위 | `experiments/`, `docs/`, `.github/`만. 앱·백엔드 파일 변경 없음 |
| CI | `experiments`, `validate`, `landing-restoration-e2e`, `mobile-*` 통과. `webkit-e2e` 1건 실패 |

`webkit-e2e` 실패는 언어 전환 화면 테스트의 클릭 시간 초과 1건입니다. PR이 앱 파일을 바꾸지 않으므로
간헐 실패로 보고 실패한 작업만 다시 돌렸습니다. 결과는 PR 화면에서 확인해야 합니다.

**병합 준비 판단**: 아직 아닙니다. Draft 상태입니다. main보다 뒤처져 있습니다. `webkit-e2e` 재실행 결과도
남았습니다. CUDA 작업은 PR #726 범위를 넓히지 않도록 별도 브랜치에 두었습니다. PR #726이 먼저 병합되면
이 브랜치를 main 위로 다시 올려 별도 PR로 내면 됩니다.

## 2. Colab 원본 감사 핵심

자세한 내용은 [감사 보고서](COLAB-T4-RUN-AUDIT.ko.md)와
[기계 판독용 기록](runs/colab-t4-20261030/colab_execution_audit.json)에 있습니다.

- 토큰 생성 3/3 성공, JSON 계약 3/3 통과. 종료 이유는 기록되지 않았습니다.
- 4번 셀은 수정 후 재실행하지 않았습니다. 지금 소스와 저장된 출력이 짝이 맞지 않습니다.
- 가중치 SHA-256과 실제 양자화 방식은 노트북에서 확인하지 않았습니다.
- 셀 실행 번호가 모두 비어 있어 실행 순서를 증명할 수 없습니다.

## 3. CUDA 실행 경로

| 파일 | 역할 |
|---|---|
| [configs/artemis_cuda_runtime.json](../configs/artemis_cuda_runtime.json) | 체크포인트·revision, 메타데이터와 가중치 SHA-256, NF4 설정, 최소 패키지 버전, Colab 관측 버전, 한도 |
| [waymaker_ai/cuda_policy.py](../waymaker_ai/cuda_policy.py) | ML 패키지 없이 정책 검증, 스냅샷 확인, 실행 기록 검증, 집계 출처 검증 |
| [gemma4_cuda_runtime.py](gemma4_cuda_runtime.py) | 사전 검사, 모델 로딩, 양자화 검사, 생성, 결과 분류 |
| [probe_gemma4_cuda.py](probe_gemma4_cuda.py) | Colab 세 사례를 다시 돌리고 실행 기록을 남기는 명령 |
| [artemis_runner.py](artemis_runner.py) | `--adapter cuda_transformers` 추가. 모델을 한 번 올려 여러 사례에 씁니다 |
| [waymaker_ai/foundation.py](../waymaker_ai/foundation.py) | `metric_group`이 CUDA 출처를 별도 기준으로 검증 |

요구사항별 구현:

- **고정 체크포인트**: `google/gemma-4-E4B-it@ee0ef60…`만 받습니다. 기존 foundation 설정의
  `upstream`, `upstream_revision`과 다르면 정책 로딩이 실패합니다. 다른 revision으로 대체하지 않습니다.
- **출처 검증**: 메타데이터 5개 파일의 SHA-256을 Hub git blob ID와 대조해 고정했습니다.
  `model.safetensors`(15,992,595,884바이트)와 `tokenizer.json`은 Hub LFS SHA-256으로 확인합니다.
  `--size-only-weights`로 해시를 건너뛰면 기록에 `size_only`가 남고 집계에서 빠집니다.
- **NF4 4비트**: 설정 요청에서 끝내지 않습니다. 올라간 모듈의 `Linear4bit` 개수, 양자화 종류,
  이중 양자화, 연산 dtype, 매개변수 장치(`cuda:0`)를 읽습니다. 하나라도 다르면 `quantization_not_verified`로 실패합니다.
- **입력 허용 목록**: 기존 `inference_input.project_inference_item`을 그대로 씁니다. 정답, 채점 기준,
  검토 정보는 프롬프트에 들어가지 않습니다. 근거 ID가 비었거나 겹치면 프롬프트를 만들기 전에 거절합니다.
- **응답 스키마와 인용 ID**: MLX 경로와 같은 시스템 프롬프트와 `parse_response`를 씁니다.
  근거 목록에 없는 ID를 인용하면 `generated_but_invalid`입니다.
- **메트릭**: 프롬프트 토큰, 생성 토큰, 종료 이유(`eos`/`length`), 전체 시간, 프리필 포함 첫 토큰 시간,
  디코딩 속도, 사례별 최대 할당·예약 메모리, 로딩 시간과 로딩 최대 메모리, `nvidia-smi` 상태.
- **상태 분류**: `completed`(토큰 생성과 스키마 통과), `generated_but_invalid`, `failed`
  (`input_rejected`, `prompt_rejected`, `generation_no_tokens`, `memory_resource_rejection`,
  `model_loading_error`, `quantization_not_verified` 등), `not_executed`(체크포인트·패키지·GPU 없음).
- **분리 집계**: CUDA 출처는 런타임 `transformers_cuda`, 체크포인트 `google/gemma-4-E4B-it`로
  MLX와 집계 키가 다릅니다. 섞으면 `require_same_metric_group`이 거절합니다.
  가중치 SHA-256, 양자화 검사, CUDA 장치 이름 중 하나라도 빠지면 집계 키를 만들지 않습니다.

노트북에서 고친 호환성 문제: `hf_device_map` 대신 매개변수 장치를 읽습니다. `skip_special_tokens=True`로
가려지던 종료 이유를 토큰 ID로 판정합니다. 사례 간 최대 메모리를 매번 초기화합니다.

## 4. 실행 기록 형식

스키마 `waymaker-artemis-cuda-run/1.0`. `cuda_policy.validate_run_record`가 저장 전에 검사합니다.

```text
schema_version, project, runtime=transformers_cuda, inference_kind=real_inference
evidence_kind: none | synthetic | candidate_unreviewed
model: checkpoint, revision, quantization, quantization_policy
environment: packages, python, platform, cuda_device, nvidia_smi
provenance: snapshot_revision, metadata_sha256, artifact_integrity, weight_integrity
load: load_seconds, load_peak_*_bytes, quantization{passed, linear4bit_modules, ...}
cases[]: case_id, execution_status, raw_output, generated_token_count, finish_reason,
         prompt_tokens, metrics{...}, output_validation, failure_category, error
execution_status, not_executed_reason, official_gold_accuracy=null, legal_accuracy_claimed=false
```

검사기가 거절하는 경우: 공식 정확도 값이 들어 있음, 근거 종류 미선언, 실행 기록인데 GPU 이름이나 패키지
버전 없음, 생성 토큰 0개인데 `completed`, 스키마 실패인데 `completed`, `not_executed`인데 생성 토큰이 있음.

이 맥에서 만든 실제 기록: [runs/mission005c-cuda-20261030/local_macos_preflight_not_executed.json](runs/mission005c-cuda-20261030/local_macos_preflight_not_executed.json)
(체크포인트 없음, torch·transformers·bitsandbytes 없음, GPU 없음).

## 5. 재현 노트북

[notebooks/artemis_gemma4_e4b_cuda_colab.ipynb](notebooks/artemis_gemma4_e4b_cuda_colab.ipynb).
순서는 실험 폴더 sparse clone, bitsandbytes 설치, 고정 revision 다운로드(이 셀만 가중치를 받음),
`probe_gemma4_cuda.py`로 세 사례 실행, 기록 파일 내려받기입니다. 출력은 비워 두었고 토큰을 쓰지 않습니다.

이 노트북은 **아직 실행하지 않았습니다**. 005-C.1에서 코드 커밋과 패키지 버전을 고정한 판으로 바꿨습니다.
16GB 다운로드는 무료 Colab 런타임 안에서 일어나 추가 비용이 없습니다. 실행 여부는 사용자가 정합니다.

## 6. 회귀 검사 결과

`experiments/waymaker-ai`에서 CI와 같은 Python 3.11 환경으로 실행했습니다.

| 명령 | 결과 |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests` | 1,607 passed, 28.83초 (새 `test_cuda_runtime.py` 46건 포함) |
| `python -m pytest -q -p no:cacheprovider tests/test_cuda_runtime.py` | 46 passed, 0.20초 |
| `python artemis_bootstrap/check_model_identity.py` | 종료 0, `PASS`, 332개 파일, 위반 0 |
| `node ../../scripts/build_procedure_classifier_lexicon.cjs --check` | 종료 0 |
| `python -m waymaker_ai.dataset.validate datasets/benchmark/v0` | 종료 0 |
| `python -m waymaker_ai.evaluation.runner ... --fail-on-hard-gates wlie` | 종료 0 |
| `python ../../scripts/check_bfixed_metrics.py ...` | `PASS` |
| `python artemis_bootstrap/probe_gemma4_cuda.py --out …` | 종료 3, `not_executed` (GPU 없는 맥에서 예상한 결과) |

새 테스트는 가짜 torch·bitsandbytes 모듈로 분류와 출처 검사만 확인합니다. 모델이 돌아간다는 증거는 아닙니다.
CI에는 GPU가 없으므로 기존 workflow가 이 테스트를 그대로 실행합니다. 실제 GPU 통합 검사는 CI 성공 조건에 넣지 않았습니다.

## 7. 평가 준비: 개발 후보 20건

이번에는 20건 GPU 평가를 돌리지 않았습니다. 다음 실행 계획입니다.

1. 위 재현 노트북을 새로 실행해 세 사례 기록을 만듭니다. 2026-10-30 기록을 재사용하지 않습니다.
   `weight_integrity: sha256_verified`, `quantization.passed: true`가 아니면 다음 단계로 가지 않습니다.
2. 같은 Colab 세션에서 `artemis_runner.py --adapter cuda_transformers --mode candidate_eval
   --benchmark artemis_bootstrap/benchmarks/artemis_eval_dev_20.json --cuda-max-new-tokens 256`을 돌립니다.
   모델은 한 번만 올립니다. T4 기준 20건은 사례당 수 초~수십 초로 예상하지만 측정값이 아닙니다.
3. 보호 장치:
   - 결과는 `transformers_cuda` 집계 키로만 묶습니다. MLX 결과, mock, 녹화 응답과 섞지 않습니다.
   - 20건은 모두 검토 전 후보입니다. 통과율은 진단 수치이며 Official Gold Accuracy는 `N/A`로 둡니다.
     독립 법률 검토 전에는 gold로 승격하지 않습니다.
   - held-out 40건은 저장소에 정답이 함께 있어 `isolation_not_verified`입니다. 독립 미공개 평가로
     부르지 않고, 이번 계획에서도 돌리지 않습니다. 기존 격리 manifest 정책을 그대로 따릅니다.
   - 근거 없이 내놓은 법률 답변(인용 없는 `answered`, 목록 밖 인용)은 성공으로 세지 않습니다.
     목록 밖 인용은 `parse_response`가 막고, 필수 인용 누락은 `artemis_eval`의 `citation_accuracy`
     차원(`missing_citations`)이 실패로 기록합니다. 사례별 결과에서 이 실패를 따로 셉니다.
   - FP16 넘침 확인을 위해 빈 응답, 반복 토큰, `length` 종료 비율을 따로 봅니다.

## 8. 다음 단계와 남은 차단 요인

| 차단 요인 | 필요한 결정·작업 |
|---|---|
| ~~브랜치 미푸시~~ | 005-C.1 시점에 해결: 푸시됨 |
| 새 CUDA 실행 없음 | 재현 노트북을 무료 T4에서 실행해 새 기록을 `runs/` 아래에 추가 |
| PR #726 병합 전 | `webkit-e2e` 재실행 결과 확인, main 반영, Draft 해제는 사용자 결정 |
| ~~CUDA PR 미생성~~ | 005-C.1 시점: PR #730(Draft)이 있고 base는 PR #726 브랜치 |
| 독립 검증자 없음 | gold 승인, held-out 독립 평가는 계속 불가 |
| MLX 경로 | 이 맥에서는 스왑 한도 때문에 여전히 `not_executed` |

## 하지 않은 것

- Colab 실행, GPU 인스턴스 생성, 모델 재다운로드, 유료 API 호출. 추가 지출 0원.
- 푸시, PR 생성, 병합, 배포(005-C 작업 범위 기준. 이후 푸시와 PR #730은 005-C.1 보고서 참고).
- 20건 GPU 평가, gold 승인, 법률 정확도 주장.
- 노트북 비밀값 확인을 넘어선 Colab 계정 접근(원본 Colab URL은 열지 않았습니다).
