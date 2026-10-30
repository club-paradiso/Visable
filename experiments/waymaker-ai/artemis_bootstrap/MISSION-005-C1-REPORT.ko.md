# Mission 005-C.1 보고서: PR #730 감사 대응과 CUDA 재현성

작성일 2026-10-30. 대상은 PR #730(Draft), 브랜치 `feat/artemis-cuda-colab-inference`입니다.

> **갱신 (Mission 005-C.2)**: 아래 표의 "New integrated CUDA runtime: not_executed"는 005-C.1 시점 상태입니다.
> 그 뒤 커밋 `59858c5`가 무료 Colab T4에서 실제로 실행되어 합성 3건이 `completed`, 기록 자체 검사가 통과했습니다.
> 42개 층 NF4 검사도 실제 모듈 이름에서 통과했습니다. [Mission 005-C.2 보고서](runs/mission005c2-cuda/MISSION-005-C2-REPORT.ko.md)를 보세요.

## 최종 상태

| 항목 | 상태 |
|---|---|
| Original Colab CUDA inference | previously observed, not independently rerun |
| New integrated CUDA runtime | **not_executed** (실제 GPU 실행 없음) |
| MLX inference | not_executed |
| Official Gold Accuracy | N/A |
| Independent legal review | not_verified |

2026-10-30 Colab 실행은 노트북에 직접 쓴 코드로 돌린 것입니다. 저장소의 새 CUDA 런타임으로 돌린 실행이 아니며,
새 런타임 결과로 쓰지 않습니다.

## 1. PR 구조

| PR | base | head | 상태 |
|---|---|---|---|
| #726 | `main` | `feat/artemis-mission005-a` @ `d9a079d` | Draft, 미병합 |
| #730 | `feat/artemis-mission005-a` (변경 전 `main`) | `feat/artemis-cuda-colab-inference` | Draft로 전환 |

#730 브랜치는 #726의 head `d9a079d` 바로 위에 쌓여 있어, base만 바꾸면 되었습니다. 강제 푸시는 하지 않았습니다.
base 변경 직후 #730의 diff는 CUDA 커밋 1개, 14개 파일이었고 #726 변경은 빠졌습니다. 이번 작업 커밋도 모두
`experiments/waymaker-ai/` 안의 CUDA 관련 파일과 공용 응답 계약만 바꿉니다.

#726이 먼저 병합되면 GitHub가 #730의 base를 `main`으로 바꾸도록 안내합니다. 그때 diff가 CUDA 변경만 남는지 다시 확인하면 됩니다.

## 2. 수정 전 결함 재현

수정 전 커밋 `a91feb0`에서 아래가 모두 그대로 통과했습니다.

| 입력 | 수정 전 | 수정 후 |
|---|---|---|
| 모델 ID를 `google/gemma-3-4b-it`로 바꾼 완료 기록 | 통과 | 거절 |
| 모델 ID를 `google/gemma-4-E2B-it`로 바꾼 완료 기록 | 통과 | 거절 |
| 잘못된 revision | 통과 | 거절 |
| 출처 정보가 하나도 없는 완료 기록 | 통과 | 거절 |
| 로딩·양자화 정보가 없는 완료 기록 | 통과 | 거절 |
| 원본 출력이 `{}`인데 `completed` | 통과 | 거절 |
| `answered`인데 인용 0개 | 통과 | 거절 |
| JSON 키 `status` 중복 | 통과 | 거절 |
| 같은 인용 ID 두 번 | 통과 | 거절 |
| 모델 로딩 실패를 러너가 표시한 상태 | `not_executed` | `failed` |

## 3. 수정 내용

**실행 기록 검증** (`waymaker_ai/cuda_policy.py`)
- 생성된 사례가 하나라도 있으면 모델 출처 전체를 요구합니다: 공식 E4B ID, 정확한 revision, `transformers_cuda`
  런타임, `real_inference`, 메타데이터 SHA-256 일치, 가중치·토크나이저 SHA-256이 고정값과 일치,
  고정된 Hub 참조 주소, 올라간 모듈 기준 NF4 검증(42개 디코더 층 전부, `nf4`, 이중 양자화, FP16 연산,
  모든 매개변수·버퍼가 `cuda:0`), 로딩 시간, CUDA 장치 이름, 패키지 버전, 소스 파일 SHA-256.
- 사례마다 원본 출력을 응답 계약으로 다시 판정합니다. 저장된 `passed` 값만으로는 `completed`가 되지 않습니다.
  `completed`는 원본 출력이 계약을 통과하고 저장된 응답과 같아야 합니다. `generated_but_invalid`는 실제로 계약을 통과하지 못해야 합니다.
- 전체 상태는 사례 상태에서 계산한 값과 같아야 합니다. `not_executed`는 사례를 담을 수 없습니다.
- 이 검사는 우리 코드가 쓴 JSON의 일관성 검사입니다. 모든 필드를 일관되게 위조한 기록은 막지 못합니다.
  외부 인증이나 암호학적 증명이 아닙니다.

**응답 계약** (`waymaker_ai/response_contract.py`, MLX와 CUDA 공용)
- JSON 키 중복, 인용 ID 중복을 거절합니다.
- `answered`, `partial`, `conflict`는 목록 안의 인용이 1개 이상 있어야 합니다. `answered`, `partial`은 답변이 비면 안 됩니다.
- 2026-10-30 Colab 출력 3개는 새 계약도 통과합니다(테스트로 확인).
- MLX 작업자는 같은 함수를 가져다 씁니다. MLX 실행 경로는 그대로 두었습니다.

**집계 분리** (`foundation.metric_group`)
- CUDA 집계 키는 `adapter_type: cuda_transformers`와 고정 가중치 SHA-256이 있어야 만들어집니다.
  mock이나 녹화 응답에 `transformers_cuda`를 붙여도 다른 집계 키가 되어 섞이지 않습니다.

**러너와 런타임**
- 모델 로딩이나 NF4 검사가 시작된 뒤 실패하면 러너는 `failed`로 기록합니다. 체크포인트·패키지·GPU가 없을 때만 `not_executed`입니다.
- `generated_but_invalid` 응답은 채점에서 통과로 세지 않고 실행 상태도 `failed`가 됩니다(테스트로 확인).
- 로딩 실패, NF4 검사 실패, 생성 중 메모리 부족 뒤에 모델 참조를 지우고 `torch.cuda.empty_cache()`를 부릅니다.
- 패키지 버전이 감사한 실행(torch 2.11.0+cu130, transformers 5.20.2, bitsandbytes 0.50.2)과 다르면
  실행을 막습니다. `--allow-version-drift`로 돌리면 `reproduction_pins_matched: false`가 기록됩니다.
- accelerate, huggingface-hub, tokenizers는 원래 실행에 버전 기록이 없어 고정하지 않았습니다.
  실행할 때마다 실제 버전을 기록하고 `pip check` 결과를 출력합니다.
- 기록 자체 검사에 실패해도 원본 출력이 담긴 기록은 저장하고, `record_validation.passed: false`와 종료 코드 4를 냅니다.
- 중첩된 출처 메모, 검토 정보, 정답은 프롬프트에 들어가지 않습니다(테스트로 확인).

## 4. 노트북

[notebooks/artemis_gemma4_e4b_cuda_colab.ipynb](notebooks/artemis_gemma4_e4b_cuda_colab.ipynb)

- 코드는 커밋 `59858c507ca48e8429b31baebbd96ca9a5ef5cda`를 SHA로 받습니다. 노트북은 그다음 커밋에 들어가므로
  자기 커밋을 가리키는 순환 참조가 없습니다. 같은 방식으로 이 맥에서 받아 보니 27MB, HEAD가 그 SHA와 일치했습니다.
- 순서: GPU·VRAM·디스크 확인 → 무료 런타임 직접 확인(`FREE_TIER_CONFIRMED`, T4 이름 확인) → 코드·패키지 고정 →
  체크포인트 다운로드와 SHA-256 → CUDA 사전 검사 → 모델 로딩 → NF4 검증 → 합성 3개 실행 → 기록 저장 → 내려받기와 런타임 연결 해제 안내.
- 출력은 비어 있고, 메타데이터에 `execution_status: not_reexecuted`를 기록했습니다.

## 5. 검증 결과

`experiments/waymaker-ai`, CI와 같은 Python 3.11 환경에서 실행했습니다.

| 명령 | 결과 |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests` | 1,671 passed (이전 1,607건 + 새 64건) |
| `python -m pytest -q tests/test_cuda_provenance_hardening.py tests/test_cuda_runtime.py` | 통과. 새 위조·회귀 테스트 포함 |
| `python artemis_bootstrap/check_model_identity.py` | 종료 0, `PASS` |
| `bash scripts/check_repo.sh` (저장소 루트) | 종료 0, 14단계 모두 통과 |
| `git diff --check` | 출력 없음 |
| `python artemis_bootstrap/probe_gemma4_cuda.py --out …` (고정 커밋 사본) | 종료 3, `not_executed` |

- `check_repo.sh`는 이 작업 폴더에 `node_modules`가 없어 처음에 `jsdom`을 찾지 못하고 멈췄습니다.
  같은 `package.json`을 쓰는 `~/dev/Paradiso`의 `node_modules`를 잠시 연결해 다시 돌렸고, 끝난 뒤 연결을 지웠습니다.
- 정체성 검사기는 새 테스트 파일이 Gemma 3 위조 사례를 담고 있어 처음에 실패했습니다. 기존
  `test_artemis_foundation.py`와 같은 방식으로 "명시적 거절 테스트" 예외에 추가했습니다.
- 기존 테스트 46건 중 일부는 느슨한 가짜 기록을 썼습니다. 검사 내용은 그대로 두고 가짜 기록만 새 기준에 맞췄습니다.
- GitHub Actions 결과는 PR #730 화면에서 확인합니다. 이 보고서를 쓰는 시점의 결과는 최종 응답에 적습니다.

## 6. 실제 CUDA 재실행

**실행하지 않았습니다.** 앱 안 브라우저에서 Colab을 열었지만 Google 계정에 로그인되어 있지 않았습니다.
비밀번호 입력은 이 작업에서 할 수 없으므로 무료 런타임을 확인하거나 실행할 수 없었습니다.

직접 실행하는 방법:
1. Colab에서 **파일 → 노트 열기 → GitHub**, 저장소 `club-paradiso/Visable`, 브랜치 `feat/artemis-cuda-colab-inference`,
   파일 `experiments/waymaker-ai/artemis_bootstrap/notebooks/artemis_gemma4_e4b_cuda_colab.ipynb`.
2. 런타임 유형 `T4 GPU`, 리소스 화면에서 무료 상태 확인 뒤 `FREE_TIER_CONFIRMED = True`.
3. 위에서부터 차례로 실행. 마지막 셀이 `artemis_cuda_record_<시각>.json`을 내려받습니다.
4. 그 파일을 고치지 않고 `runs/` 아래 새 폴더에 넣습니다. 실행이 끝나면 런타임 연결을 해제하고 삭제합니다.

합성 3개만 실행합니다. 개발 후보 20건과 held-out 40건은 실행하지 않습니다.

## 7. 남은 문제

| 등급 | 내용 |
|---|---|
| P1 | 새 CUDA 런타임이 실제 GPU에서 한 번도 실행되지 않았습니다. NF4 층 검사(정규식 `language_model.layers.N.mlp.`)는 Gemma 4 실제 모듈 이름으로 확인되지 않았습니다. 이름이 다르면 안전한 쪽(`quantization_not_verified` 실패)으로 막힙니다 |
| P1 | PR #726이 Draft이고 미병합입니다. #730은 그 위에 쌓여 있어 먼저 병합될 수 없습니다 |
| P2 | accelerate, huggingface-hub, tokenizers 버전을 고정하지 못했습니다(원래 실행에 기록 없음) |
| P2 | T4에서 bf16 체크포인트를 FP16으로 돌리는 수치 안정성은 긴 입력에서 확인하지 않았습니다 |
| P2 | `check_repo.sh`의 Node 단계는 다른 체크아웃의 `node_modules`로 돌렸습니다 |

## 8. 병합 준비 판정

**아직 아닙니다.** 코드·테스트·문서는 리뷰를 받을 수 있는 상태입니다. 다만 새 런타임의 실제 GPU 실행 기록이 없고,
#726이 먼저 병합되어야 합니다. 다음 순서를 권합니다.
1. 사용자가 무료 T4에서 노트북을 실행하고 기록 파일을 저장소에 추가합니다.
2. 기록이 `record_validation.passed: true`이고 세 사례 상태가 확인되면 #730 Draft를 해제할지 정합니다.
3. #726 병합 뒤 #730 base가 `main`으로 바뀌면 diff와 CI를 다시 확인합니다.
