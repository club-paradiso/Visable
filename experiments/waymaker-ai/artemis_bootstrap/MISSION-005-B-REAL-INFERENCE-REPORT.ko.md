# Waymaker Artemis — Mission 005-B 실제 추론 점검

작성일: 2026-10-30. 기준 커밋: `02e29e241334c6f6ff742483c984efc2142ad2ad`.
결과는 **`not_executed`**입니다. 전용 런타임과 실제 프로세서·tokenizer·템플릿은
준비했지만, 스왑 사용량이 기존 상한을 넘어 모델 로딩 전에 중단했습니다.
**Official Gold Accuracy = N/A**, 학습은 `not_executed`, 배포는
`not_authorized`, 독립 법률 평가는 `not_verified`입니다.

## 처음 확인한 상태

로컬과 원격은 기존 `feat/artemis-mission005-a`의 기준 커밋으로 일치했고
사용자 미커밋 변경은 없었습니다. PR #726은 open·Draft이며 기준 커밋의
Waymaker AI Experiments와 Repo Validation은 모두 success로 완료됐습니다.
관련 워크트리를 확인하고 루트 지침, 공통 모델 설정, 이전 추론·추가 감사
보고서, 런타임·probe·회귀 테스트와 Mission 005-B 계획을 읽었습니다.

장비는 Apple M1, 통합 메모리 8,589,934,592 bytes, macOS 15.6.1
(24G90), arm64입니다. 초기 디스크 여유는 약 9.26GB, 스왑 사용은 약
2.76GB였습니다. 과거의 디스크 12.63GB·스왑 1.44GB를 현재 값으로 사용하지
않았습니다. 디스크 기준은 충족했지만 스왑은 처음부터 2GB 상한을 넘었습니다.

## 전용 환경 복구

이 체크아웃의 `artemis_bootstrap/.venv`에 Python 3.11.15 환경을 새로
만들었습니다. `include-system-site-packages`는 false입니다. 전역 패키지와
관련 워크트리의 개발·검증 환경은 수정하지 않았습니다.

설치 전에 pip dry-run과 각 wheel의 크기·해시를 확인했습니다. MLX-VLM의
선언된 의존성과 그 전이 의존성 74개를 고정했습니다. 설치용 wheel 합계는
218,885,093 bytes이며 최대 파일은 약 48.3MB였습니다. 모델·데이터셋은
다운로드하지 않았습니다. 설치 공간 예산을 약 1.56GB로 잡아도 디스크
6GB 여유 기준을 지킬 수 있음을 확인했습니다.

[해시 고정 lock](requirements-mlx-vlm-0.7.11.lock)을 `--require-hashes`,
`--only-binary=:all:`, `--no-cache-dir`, `--no-deps`로 설치했습니다. 이는
미리 검토한 전체 의존성을 같은 버전으로 설치하기 위한 옵션입니다.
설치는 종료 0, 약 43.20초였고 디스크 여유는 약 9.23GB에서 8.15GB로
바뀌었습니다. 설치 중에도 디스크 6GB 기준을 감시했습니다.
`pip check` 결과는 “No broken requirements found.”입니다.

| 주요 패키지 | 실제 설치 버전 |
|---|---|
| MLX / mlx-metal | 0.32.4 / 0.32.4 |
| MLX-VLM | 0.7.11 |
| Transformers / tokenizers | 5.20.2 / 0.23.3 |
| huggingface-hub | 2.3.0 |
| Pillow | 13.0.0 |

나머지 버전, 내려받은 파일의 URL·크기·해시와 설치 로그는 실행 디렉터리에
있습니다. MLX-VLM 서버·UI 배포 서비스를 시작하지 않았습니다.

## 실제 확인한 호환성 단계

설치된 0.7.11 소스를 읽고 load/generate/template 시그니처, Gemma 4 모델
클래스, 로컬 checkpoint 처리와 메모리 제어 API를 확인했습니다. 실제
import 검사에서는 문제가 없었습니다. 기존 streaming 검증기로 tokenizer,
인덱스, 모든 shard의 SHA-256도 다시 확인했습니다. 계열·구조·양자화·프로세서
설정과 revision은 공통 설정과 일치했습니다.

가중치를 MLX 모델로 로드하지 않는 별도 점검에서 실제 `Gemma4Processor`,
`GemmaTokenizer`, 텍스트 채팅 템플릿을 초기화했습니다. 준비된 입력은
127토큰입니다. 메모리 제어 API 호출도 성공했습니다. 이 점검의 전체 시간은
무결성 검사와 초기화를 포함해 약 5.75초, 프로세스 최대 RSS는 약 808.8MB입니다.
이를 모델 로딩 시간이나 prefill 성능으로 보고하지 않습니다.

초기 프로세서 점검 코드가 `load_processor`에 문자열 경로를 전달해
`TypeError: unsupported operand type(s) for /: 'str' and 'str'`로 실패했습니다.
설치된 구현에서 Path 연산을 확인하고 해당 인수만 Path로 바꿨습니다.
실패 기록을 보존하고, 가중치 로딩 없이 Path 인수를 확인하는 회귀 테스트를
추가한 뒤 재점검에 성공했습니다. 기존 모델 `load()`는 문자열 경로를
지원하므로 그 API를 임의로 바꾸지 않았습니다.

프로세서 초기화에서는 mel filter 관련 경고 1건이 나왔습니다. 원문을
기록했으며 오디오 입력은 사용하지 않았습니다. 경고를 숨기거나 실제 모델
실행까지 성공한 것으로 해석하지 않았습니다.

## 32토큰 probe의 실제 결과

`experiments/waymaker-ai`에서 저장소의 기존 probe를 실행했습니다.

```bash
artemis_bootstrap/.venv/bin/python artemis_bootstrap/probe_gemma4.py \
  --python /Users/seonjaekim/dev/Visable-artemis-gemini/experiments/waymaker-ai/artemis_bootstrap/.venv/bin/python \
  --max-tokens 32 \
  --out artemis_bootstrap/runs/mission005b-real-inference/20261030T005944Z/raw_inference_32.json
```

모델은 `mlx-community/gemma-4-e4b-it-4bit`, revision은
`475b9088d29754a3379866cf5aeb6b41acd313c2`입니다. 질문은
“체류기간을 연장하려면 어떤 사항을 확인해야 하나요?”이며 증거는 없습니다.

종료 코드는 **3**, 상태는 **not_executed**, 분류는
`memory_resource_rejection`입니다. 기록된 사유는
`Swap pressure: 2.73 GB used; limit 2.0 GB`입니다.
디스크 여유는 약 7.98GB, 스왑은 2.7264GB였고 전후 값은 같았습니다.
회귀 검증 후의 별도 자원 점검에서도 스왑 약 3.51GB로 상한을 넘었습니다.
모델 로딩·생성은 시작하지 않았습니다. 원문 응답, 생성 토큰 수, 출력 파싱
결과와 모델 성능 값은 없으며 null 또는 미실행 사유로 기록했습니다.

최고 도달 단계는 **실제 프로세서·tokenizer·템플릿 초기화**입니다.
실제 모델 생성이 없으므로 64/128토큰 재시도와 추가 A/B/C 생성 검사는
수행하지 않았습니다. 실제 모델로 개발 20건과 홀드아웃 40건을 평가하지 않았습니다.
스왑·디스크·메모리 제한과 120초 timeout을 완화하지 않았습니다.

## 기록 분류와 회귀 검증

기존 worker는 토큰 생성 후 JSON 검증에 실패해도 모델 로딩 오류와 같은
failed로 기록했습니다. 합성 API 결과로 이 문제를 재현하고 다음을 구분했습니다.
완료는 토큰 수가 양수이고 구조 검증까지 통과한 경우로 제한했습니다.

- `completed`: 실제 토큰 생성과 구조 검증 성공
- `generated_but_invalid`: 토큰은 생성됐지만 JSON·스키마 검증 실패
- `failed`: 로딩·생성 오류 또는 생성 토큰 확인 실패
- `not_executed`: 사전 조건·자원 검사로 생성 전에 중단

원문을 수정해 파싱을 통과시키지 않습니다. 출력 제한 도달 가능성,
finish reason, 단계와 오류 분류를 기록합니다. API 회귀용 합성 결과는
pytest 임시 디렉터리에만 남으며 실제 추론 증거와 합치지 않습니다.
런타임 import가 메모리 상태를 바꿀 수 있으므로 import 직후에도 자원을
재측정합니다. import 뒤 스왑이 상한을 넘는 경우를 실패 테스트로 재현하고
모델 로딩 전에 거부하도록 보강했습니다. 기존 제한 값은 바꾸지 않았습니다.

기존 증거 허용 목록, 모델 출처·무결성, 골드 제한, 격리 상태와 보안 테스트를
보존했습니다. 기존 벤치마크·원장·과거 실행 기록·외부 캐시는 재작성하지
않았습니다. 전체 테스트와 저장소 검사, 최종 head의 CI 결과는 아래 검증
기록과 기존 PR의 Checks에서 확인합니다.

| 실제 실행한 검사 | 결과 |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests` | 최종 1,561 passed, 26.55초. 기존 1,551건과 새 합성 API 회귀 10건 포함 |
| runtime·foundation·post-audit 대상 검사 | 최종 57 passed, 0.63초 |
| `PATH=/Users/seonjaekim/dev/Paradiso/.venv-check/bin:$PATH bash scripts/check_repo.sh` | 종료 0, 백엔드 회귀 및 지식 평가 69/69 통과 |
| `python3 artemis_bootstrap/check_model_identity.py` | PASS, 위반 0건 |

테스트용 Python은 기존 `/Users/seonjaekim/dev/Paradiso/.venv-check/bin/python`을
읽기만 했습니다. Node 의존성은 기존 설치를 임시 심볼릭 링크로 사용한 뒤
링크만 제거했습니다. 검증 환경의 패키지를 업그레이드하거나 전용 추론
환경의 패키지로 교체하지 않았습니다. 추가 변경을 푸시한 뒤의 원격 CI는
기존 PR 최종 head의 Checks와 최종 작업 보고서에 따로 기록합니다.

## 남은 차단 요인과 다음 단계

현재 차단 요인은 **기존 스왑 사용량이 2GB 상한을 넘는 상태**입니다.
이번 기록만으로 M1 8GB에서 E4B 실행이 불가능하다고 단정할 수는 없습니다.
다음 실행 전에는 최소 디스크 6GB 이상, 스왑 2GB 이하, 같은 runtime과
체크포인트 무결성 조건을 모두 충족해야 합니다. 다른 앱을 임의 종료하거나
스왑을 초기화하는 방식으로 기준을 맞추지 않았습니다.

대체 장비의 실용적인 시작점은 Apple Silicon·macOS 15 이상, 통합 메모리
16GB 이상과 디스크 10GB 이상 여유입니다. 이는 검증된 최저 사양이 아닌
엔지니어링 추정입니다. 기존 MLX 6GB 상한과 기타 안전 제한을 그대로
유지한 상태에서 실제 peak 메모리를 측정해야 합니다. 유료 장비를 자동으로
빌리거나 다른 가중치로 대체하지 않았습니다.

32토큰 실제 생성과 구조 검증을 확인한 다음, 안전한 경우에만 합성 A/B/C
검사로 넘어갑니다. 개발 20건 평가는 그 뒤의 별도 단계입니다. 독립적인
접근 통제·법률 검토 전까지 격리는 `isolation_not_verified`, 공식 골드
정확도는 N/A를 유지합니다.

증거 위치: [실행 디렉터리](runs/mission005b-real-inference/20261030T005944Z/),
[실행 manifest](runs/mission005b-real-inference/20261030T005944Z/execution_manifest.json),
[원본 probe 기록](runs/mission005b-real-inference/20261030T005944Z/raw_inference_32.json),
[자원·성능 보고서](runs/mission005b-real-inference/20261030T005944Z/resource_performance_report.json),
[후속 계획](runs/mission005b-real-inference/20261030T005944Z/FOLLOW-UP-PLAN.md).
