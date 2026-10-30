# Mission 005-C.2 보고서: 저장소 CUDA 러너의 실제 T4 실행

작성일 2026-10-30. 실행 시각(UTC) 2026-10-30 03:36:43~03:37:00(생성 구간), 모델 로딩은 그 직전입니다.

## 최종 상태

| 항목 | 상태 |
|---|---|
| Original Colab CUDA inference (2026-10-30 오전) | previously observed, not independently rerun |
| **New integrated CUDA runtime** | **completed** (합성 3건, 무료 Colab T4, 기록 자체 검사 통과) |
| MLX inference | not_executed |
| Official Gold Accuracy | N/A |
| Independent legal review | not_verified |

## 1. 기존 Colab 실험에서 성공한 사실

노트북에 직접 쓴 코드로 공식 E4B를 NF4로 올려 합성 3건에서 유효한 JSON을 냈습니다. 감사 결과는
[COLAB-T4-RUN-AUDIT.ko.md](../../COLAB-T4-RUN-AUDIT.ko.md)에 있습니다. 이번 실행 결과와 섞지 않습니다.

## 2. 이번 새 CUDA 러너로 실제 재현한 사실

저장소 커밋 `59858c507ca48e8429b31baebbd96ca9a5ef5cda`의 `gemma4_cuda_runtime.py`, `probe_gemma4_cuda.py`를
재현 노트북으로 무료 Colab T4에서 실행했습니다. 기록은 [raw_record.json](raw_record.json)
(10,909바이트, SHA-256 `d79ec336d4c7ae90bceed6cea9a90b42690896173de8e38eefe7a195edafdf99`)이며 고치지 않았습니다.

**환경과 출처**
- GPU Tesla T4 15,360 MiB, 드라이버 580.82.07, Python 3.13.16, 디스크 여유 75.25GB.
- torch 2.11.0+cu130, transformers 5.20.2, bitsandbytes 0.50.2 — 고정 버전과 일치, `version_drift: []`.
  accelerate 1.15.0, huggingface-hub 1.33.0, tokenizers 0.23.3은 기록만 했습니다.
  `pip check`는 Colab 기본 환경의 `ipython 7.34.0 requires jedi` 한 줄만 냈습니다(이 실행과 무관).
- 모델 `google/gemma-4-E4B-it` @ `ee0ef6023621cff504d758262d4e04895a5af4a2`. 메타데이터 5개 파일,
  `tokenizer.json`, `model.safetensors`(15,992,595,884바이트, `cfbd3d2f…`) SHA-256 모두 고정값과 일치.
- 기록의 소스 파일 해시 6개가 커밋 `59858c5`의 파일과 일치함을 로컬에서 확인했습니다. `code_files_modified_from_commit: false`.

**로딩과 NF4 검증 (실제 모듈 기준)**
- 로딩 70.19초, 로딩 중 최대 할당 9,304,240,640바이트(8.665 GiB), 예약 8.785 GiB. 로딩 뒤 `nvidia-smi` 사용량 9,117 MiB.
- `Linear4bit` 592개, 일반 `Linear` 1개. 42개 디코더 층 전부 4비트 MLP 확인(`quantized_decoder_layers: 42`).
  양자화 종류 `nf4`, 이중 양자화 `true`, 연산 `float16`, 모든 매개변수·버퍼 `cuda:0`.
- 005-C.1에서 미검증으로 남았던 층 검사 정규식이 실제 Gemma 4 모듈 이름과 맞았습니다. 코드 수정은 필요 없었습니다.

**합성 사례 3건** (가상 규칙이며 실제 법령이 아닙니다)

| 사례 | 입력/생성 토큰 | 종료 | 상태 | 인용 | 전체 시간 | 첫 토큰 | 디코딩 속도 | 최대 할당 |
|---|---|---|---|---|---|---|---|---|
| A 근거 없음 | 126 / 19 | eos | `insufficient_evidence` | 없음 | 4.21초 | 1.93초 | 7.90 tok/s | 8.743 GiB |
| B 합성 근거 | 161 / 38 | eos | `partial` | `SYN-1` | 4.64초 | 0.18초 | 8.30 tok/s | 8.751 GiB |
| C 상충 근거 | 200 / 69 | eos | `conflict` | `SYN-1`, `SYN-2` | 8.39초 | 0.19초 | 8.29 tok/s | 8.757 GiB |

- 세 건 모두 JSON 파싱, 응답 계약(인용 ID가 목록 안에 있음, 중복 없음), 실행 기록 검사를 통과했습니다.
- 사례 B 답변: "가상의 규칙에 따르면 신청은 만료일 30일 전까지 해야 합니다." 근거만으로 답할 수 있는데 `answered`가 아니라 `partial`을 골랐습니다. 원본 실행과 같은 판단입니다.
- 사례 A의 첫 토큰 1.93초에는 첫 생성의 CUDA 준비 시간이 들어 있습니다.
- 생성 토큰 수(19, 38, 69)와 상태는 원본 실행과 같았습니다. 사례 B 문장은 "가상 규칙에" → "가상의 규칙에"로 조금 다릅니다. 저장소 경로가 근거에 빈 `title`, `source`를 붙여 프롬프트가 달라졌기 때문으로 봅니다(입력 토큰 수도 다릅니다). 원인 확정은 아닙니다.
- 실행 기록에는 경고 목록 필드가 없습니다. Python 경고는 기록되지 않았습니다(남은 문제 참고).

**기록 전달 경로**: 앱 안 브라우저가 파일 내려받기를 저장하지 않고, localhost로 보내는 요청 본문도 비워서
보냈습니다. 그래서 기록 본문을 두 조각으로 읽어 조각마다 SHA-256을 맞추고, 전체 파일을 Colab에서 계산한
SHA-256과 대조했습니다. 세 지점의 해시가 같습니다([transfer_note.json](transfer_note.json)).

## 3. 단위 테스트와 실제 GPU 테스트의 차이

| | 단위 테스트(CI) | 이번 실제 GPU 실행 |
|---|---|---|
| 모델 | 가짜 torch·bitsandbytes 객체 | 공식 E4B 가중치 16GB |
| 무엇을 보나 | 상태 분류, 출처 검사, 위조 거절 | 실제 로딩, NF4 모듈, 생성, 메트릭 |
| 어디서 | GitHub Actions, GPU 없음 | 무료 Colab T4 |
| 반복 | 매 커밋 | 이번 1회. CI 성공 조건에 넣지 않음 |

실제 기록을 고정 자료로 삼아 회귀 테스트 13건을 추가했습니다([test_cuda_real_run_record.py](../../../tests/test_cuda_real_run_record.py)).
기록 원본 해시, 검사 통과, 42층 NF4, 세 사례 상태, 실제 기록을 조작했을 때의 거절, 증거 파일의 해시 연결,
MLX와 집계 분리를 확인합니다. 모델을 다시 돌리지는 않습니다.

## 4. 수정한 결함

- 실제 GPU 실행에서 코드 결함은 나오지 않았습니다. 런타임·검증 코드는 바꾸지 않았습니다.
- 추가한 것: 기록을 고치지 않고 검토용 파일로 나누는 [split_cuda_record.py](../../split_cuda_record.py), 실제 기록 회귀 테스트.

## 5. 테스트와 CI

커밋 전 로컬(CI와 같은 Python 3.11)에서 실행했습니다.

| 명령 | 결과 |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests` | 1,684 passed (이전 1,671건 + 실제 기록 회귀 13건) |
| CUDA 관련 3개 테스트 파일 | 123 passed |
| `python artemis_bootstrap/check_model_identity.py` | 종료 0 |
| `bash scripts/check_repo.sh` | 종료 0 (Node 단계는 `~/dev/Paradiso`의 `node_modules`를 잠시 연결해 실행) |
| `git diff --cached --check` | 출력 없음 |

GitHub Actions 결과는 PR #730 화면에서 확인합니다.

## 6. 비용

추가 지출 0원. Colab 리소스 화면은 "구독 중이 아닙니다", 사용 가능한 컴퓨팅 단위 0으로 표시됐고, 런타임은 무료 T4였습니다.
실행 뒤 런타임을 연결 해제·삭제했습니다.

## 7. 실행 중 일어난 일

- Colab 페이지가 실행 중 두 번 새로 고쳐졌습니다. 커널은 유지되어 실행 결과는 잃지 않았습니다. 새로 고침 뒤 노트북 셀을 처음부터 다시 실행했고, 체크포인트는 캐시에서 읽었습니다(다운로드 0바이트).
- 빈 셀을 누르다 Colab의 Gemini 패널이 열려 전달용 코드가 입력란에 들어갔습니다. 보내지 않고 지운 뒤 닫았습니다.
- 페이지 스크립트가 클립보드에 무언가를 썼다는 알림이 한 번 있었습니다. 내용은 확인하지 못했습니다.

## 8. 남은 문제

| 등급 | 내용 |
|---|---|
| P2 | 실행 기록이 Python 경고를 담지 않습니다. 다음 실행 전에 `probe_gemma4_cuda.py`가 경고를 기록하도록 고치는 것이 좋습니다 |
| P2 | accelerate, huggingface-hub, tokenizers는 이번에 실제 버전을 얻었지만 아직 고정하지 않았습니다 |
| P2 | T4 FP16 실행의 긴 입력 안정성은 미확인입니다(이번 입력은 최대 200토큰) |
| P2 | 실행은 1회입니다. 탐욕적 생성이라 결과가 같을 것으로 보지만 반복 실행으로 확인하지 않았습니다 |

## 9. 병합 준비

PR별 판정은 최종 응답에 적습니다. 이 실행으로 "새 CUDA 경로의 실제 GPU 실행 성공"과 "실행 기록 검사 통과" 조건은 충족됐습니다.

## 10. Mission 005-D 진입 권고

진입을 권합니다. 계획은 [MISSION-005-D-PLAN.ko.md](../../MISSION-005-D-PLAN.ko.md)에 있습니다.
