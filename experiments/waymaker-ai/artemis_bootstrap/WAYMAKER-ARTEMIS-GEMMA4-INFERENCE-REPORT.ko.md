# Waymaker Artemis — Gemma 4 추론 점검 보고서

점검일: 2026-10-29. 결과: **not_executed**.
실제 가중치 생성 성공이나 새 모델 성능을 주장하지 않습니다.

## 체크포인트 확인

- 기반 모델: `google/gemma-4-E4B-it` @ `ee0ef6023621cff504d758262d4e04895a5af4a2`
- 추론 체크포인트: `mlx-community/gemma-4-e4b-it-4bit` @ `475b9088d29754a3379866cf5aeb6b41acd313c2`
- 변환 원본 revision: `fee6332c1abaafb77f6f9624236c63aa2f1d0187`
- 모델: `gemma4`, `Gemma4ForConditionalGeneration`, 텍스트 42층, hidden size 2560
- 프로세서: `Gemma4Processor`; 양자화: affine 4-bit / group 64
- 로컬 가중치 파일: 5,146,800,534 bytes. 전체 스냅샷 참조 파일: 5,179,241,512 bytes

원격 고정 revision의 config, processor, tokenizer config, chat template,
모델 카드와 로컬 파일의 SHA-256이 모두 일치했습니다. 가중치는 존재·크기를
확인했으며 이번에 전체 파일의 SHA-256을 다시 계산하지는 않았습니다.

## 실제 실행한 점검

```bash
python artemis_bootstrap/probe_gemma4.py \
  --python /Users/seonjaekim/dev/Visable-artemis/experiments/waymaker-ai/artemis_bootstrap/.venv/bin/python \
  --out artemis_bootstrap/runs/genesis-recovery-20261029/inference_probe.json
```

종료 코드는 3입니다. 질문은 “체류기간을 연장하려면 어떤 사항을 확인해야 하나요?”로
준비했으나, 가중치를 로드하기 전 조건 검사에서 중단했습니다.

실측 차단 사유: `Insufficient disk space: 5.41 GB; need 6.0 GB; Swap pressure: 7.53 GB used; limit 2.0 GB; mlx-vlm 0.7.11 not installed (found None)`.
이 값은 검사 시점의 값입니다. 최초 점검에서는 디스크 약 4GiB, 스왑 약
8.4GB 사용을 관측했으며 운영체제 상태에 따라 값이 달라졌습니다.

| 항목 | 관측 결과 |
|---|---|
| 하드웨어 | Apple M1, 통합 메모리 8,589,934,592 bytes |
| 설치된 MLX / mlx-metal | 0.32.4 / 0.32.4 |
| 설치된 MLX-LM | 0.32.2 — 새 어댑터가 선택하지 않음 |
| MLX-VLM | 미설치; 소스 검토 대상 0.7.11 |
| Transformers / tokenizers / huggingface-hub | 5.20.2 / 0.23.3 / 2.3.0 |
| 로딩 시간·prefill·생성 지연·tokens/s | 측정 안 함, null |
| 생성 토큰 수·모델 응답 원문 | 생성 안 함, null |
| 모델 RSS·MLX peak memory | 가중치 실행 안 함, 미측정 |
| 공식 골드 정확도 | N/A |

별도로 실제 `AutoProcessor.from_pretrained(..., local_files_only=True,
trust_remote_code=False)`를 실행했습니다. **PIL 미설치 ImportError**로 실패했습니다.
PyTorch 미설치 경고도 나왔습니다. 프로세서 초기화가 성공했다고 주장하지
않습니다. 관련 워크트리의 가상환경은 읽기만 했고 패키지를 설치하지 않았습니다.

## 구현과 남은 검증

MLX-VLM 0.7.11 wheel의 load, generate, prompt_utils, Gemma 4 소스를 읽어
호출 규격을 확인했습니다. wheel 약 3.53MB만 조사용으로 읽었고 모델을
다운로드하지 않았습니다. 새로운 어댑터의 제어 흐름·격리·메타데이터 검사는
오프라인 회귀 테스트로 확인했습니다. 실제 MLX-VLM 가중치 로딩, 한국어 생성,
구조화 응답 성공 여부는 아직 검증하지 못했습니다.

재시도하려면 독립 환경에 필요한 패키지를 설치하고 디스크·스왑 여유를
확보하거나 다른 장비를 사용해야 합니다. 그 뒤 위의 32토큰 단일 점검부터
실행합니다. 성공 전에는 후보 20건 전체 평가나 학습을 시작하지 않습니다.
기존 E4B MLX-LM 연구 기록은 과거 실행 증거로 보존하며 새 어댑터 검증과
합치지 않습니다.

증거: [실행 기록](runs/genesis-recovery-20261029/inference_probe.json),
[프로세서 점검](runs/genesis-recovery-20261029/processor_probe.json),
[평가 러너 사전 점검](runs/gemma4-e4b-recovery-preflight-20261029/run_summary.json).
모델 카드: [Google E4B](https://huggingface.co/google/gemma-4-E4B-it),
[MLX 변환본](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit).
