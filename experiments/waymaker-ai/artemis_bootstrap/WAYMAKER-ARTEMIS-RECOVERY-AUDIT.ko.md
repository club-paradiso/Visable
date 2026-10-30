# Waymaker Artemis — Genesis Recovery 감사

조사일: 2026-10-29. 재개·최종 로컬 검증: 2026-10-30.
기준 커밋: `d3e9490e22bdf455ca0bda958106811195a49d6d`.

## 원인과 복구 범위

`artemis_runner.py`의 생성자와 CLI가 Gemma 3 270M을 기본 모델로 선택했습니다.
요청한 revision이 없으면 다른 캐시 revision을 선택하는 경로도 있었습니다.
모델 정체성을 강제하는 공통 설정과 검증이 없었고, 섀도 평가는 과거 실행
디렉터리를 자동으로 읽었습니다. 이 때문에 비정규 모델의 0/20 결과가
프로젝트의 주된 실제 모델 기준선으로 보고되었습니다.

기본값 변경에 그치지 않고 공통 설정, 체크포인트 검증, MLX-VLM 프로세서 경로,
오프라인 실행 제한, 실행 출처와 지표 분리, 학습 설정 검사, CI 검사를 추가했습니다.
실제 MLX-VLM 생성은 실행 전 조건 검사에서 차단되었습니다. 코드 복구와
실제 모델의 생성 성공을 구분합니다. **Official Gold Accuracy = N/A**입니다.

## 로컬·원격 확인

대상은 `/Users/seonjaekim/dev/Visable-artemis-gemini`이며 브랜치는
`feat/artemis-mission005-a`입니다. 작업 시작 시 미커밋·미추적 사용자 파일은
없었습니다. `pwd`, `git rev-parse --show-toplevel`, `git status --short --branch`,
`git branch -avv`, `git worktree list`, `git remote -v`, `git log -5 --oneline`,
`df -h`를 실행했습니다. 재개 후에도 로컬과 원격을 다시 확인했습니다.

`origin/main` 및 원격 main은 `a17233450e4b12948d35876a86cd05e588de3fce`,
원격 작업 브랜치는 기준 커밋과 같았습니다. GitHub 연결로 확인한
[기존 PR #726](https://github.com/club-paradiso/Visable/pull/726)은 open·draft이며
병합되지 않았습니다. 이 문서는 커밋 전 로컬 검증 기록입니다. 최종 커밋과
원격 CI 결과는 같은 PR의 갱신된 설명 및 Checks에서 확인할 수 있습니다.

저장소·상위 경로에서 적용되는 지침을 조사하고 루트 `CLAUDE.md`를 읽었습니다.
저장소 내부 `AGENTS.md`는 없었으며 사용자가 제공한 공통 지침을 적용했습니다.
관련 `/Users/seonjaekim/dev/Visable-artemis`의 Git 상태와 기존 MLX 가상환경을
읽었습니다. 해당 워크트리의 파일·패키지는 수정하지 않았습니다.

## 참조 조사와 실제 정리

저장소 전체에서 `gemma[-_ ]?3|gemma3|270m|gemma-2|qwen`을 검색하고,
숨김 로컬 설정·실행 스크립트·환경 변수·프로젝트 캐시를 추가 점검했습니다.
최초 검색의 52개 경로는 아래 명세에 경로별로 분류했습니다. 백엔드의 별도
모델 정책과 `experiments/waymaker-gemma4-finetune`의 별도 Colab 실험은
Artemis 실행 경로가 아니므로 수정하지 않았습니다. 교사 모델 정책 목록은
외부 데이터 출처의 허용 여부를 검사하며 기반 모델 선택에 사용되지 않습니다.

| 분류 | 처리 |
|---|---|
| 활성 런타임 의존성 | 생성자·CLI·실행 스크립트·학습 설정을 공통 Gemma 4 정책에 연결 |
| 암묵적 대체 경로 | 임의 revision 선택과 과거 실행 자동 입력 제거 |
| 구형 생성 산출물 | Gemma 3 실행 및 이를 포함한 섀도 보고서 7개를 history로 이동 |
| 역사 기록 | Git 이력과 과거 E4B 실험 보존, 기존 README를 역사 문서로 이동 |
| 외부 캐시 | 정확한 경로·크기를 명세에 기록하고 모두 보존 |
| 무관한 코드 | 별도 Visable 앱·연구 자료 그대로 보존 |

이동한 생성 파일 7개는 원본 SHA-256을 유지했습니다. 섀도 보고서는 수정한
생성기로 다시 만들었으며 합성 7건·적대적 회귀 14건만 포함합니다. 실제 모델
그룹은 `null`입니다. 과거 Gemma 3 결과를 새 Gemma 4 결과로 바꾸지 않았습니다.
기존 README는 역사 경고와 상대 링크만 조정했습니다.

외부 Gemma 3 스냅샷 참조 크기는 190,209,914 bytes, E4B는
5,179,241,512 bytes입니다. 가중치 삭제·대형 다운로드는 하지 않았습니다.
검증용으로 만든 로컬 `node_modules` 심볼릭 링크는 기존 의존성을 읽기 위해
사용한 뒤 제거했습니다. 원래 의존성 디렉터리는 변경하지 않았습니다.

모든 변경 경로의 목적·조치·복구 방법과 캐시 목록은
[정리 명세](WAYMAKER-ARTEMIS-LOCAL-CLEANUP-MANIFEST.json)에 있습니다.

## 모델과 실행 증거

권위 설정은 `../configs/artemis_foundation.json` 하나입니다. 기본 모델은
Google Gemma 4 E4B Instruct이며 E2B는 명시적 개발 선택만 허용합니다.
checkpoint와 revision, 계열·층수·양자화·프로세서·메타데이터 해시가 맞지
않으면 실행하지 않습니다. 누락된 캐시는 다운로드나 모델 대체를 유발하지
않으며 `not_executed`로 기록합니다.

MLX-VLM 0.7.11 소스의 Gemma 4 로더·프로세서·생성 API를 확인했습니다.
기존 환경에는 해당 패키지가 없고, 실제 AutoProcessor 초기화는 PIL 미설치로
실패했습니다. 디스크 5.41GB·스왑 사용 7.53GB였던 점검 시점에는 자원 기준도
충족하지 못했습니다. 생성 시간·토큰 수·응답은 측정하거나 만들지 않았습니다.
[추론 보고서](WAYMAKER-ARTEMIS-GEMMA4-INFERENCE-REPORT.ko.md)에 원본 기록을 연결했습니다.

## 기존 기반 보존과 추가 결함 수정

후보 60건, 개발 20건·홀드아웃 40건, 블라인드 입력과 정답 분리, 법률 증거,
판본 카탈로그, 검토 패킷·원장, 독립 벤치마크 접수 및 보안 회귀를 보존했습니다.
홀드아웃은 여전히 `isolation_not_verified`입니다. 법률 원문·검토 승인은
추가하거나 바꾸지 않았습니다.

검토자 이름·날짜만으로 공식 골드로 채점될 수 있는 경로를 발견해 차단했습니다.
승격 원장과 채점기 모두 신뢰할 수 있는 외부 인증 검증기가 연결되기 전에는
공식 골드를 인정하지 않습니다. 기존 긍정 테스트를 허위 승인 거부 테스트로
강화했습니다. 임시 출력 경로로 블라인드 자료를 생성해도 저장소 매니페스트가
덮어써지는 결함도 수정했습니다. 검사 중 바뀐 매니페스트는 기준 커밋의
원본 바이트로 복원했으며 이후 전체 테스트에서도 변경되지 않았습니다.

## 실행한 검증

Python 검증 환경: `/Users/seonjaekim/dev/Paradiso/.venv-check/bin/python`
(3.11.15). 아래 `python`은 이 실행 파일이며 실험 명령의 작업 경로는
`experiments/waymaker-ai`입니다. 의존성은 기존 설치를 읽었고 추가 설치하지 않았습니다.

| 명령 | 실제 결과 |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests` | 최종 코드 검사 1,530 passed, 20.75초 |
| `python -m pytest -q -p no:cacheprovider tests/test_artemis_foundation.py tests/test_artemis_runner.py tests/test_artemis_bootstrap.py tests/test_training_configs.py` | 앞선 대상 검사 148 passed; 이후 추가 회귀도 전체 검사에 포함 |
| `python -m pytest -q -p no:cacheprovider tests/test_training_configs.py tests/test_artemis_foundation.py` | 학습 안내 정정 후 대상 검사 91 passed |
| `python -m pytest -q -p no:cacheprovider tests/test_artemis_runner.py tests/test_artemis_foundation.py` | 최종 CSV 줄바꿈·N/A 출력 수정 후 39 passed |
| `python -m waymaker_ai.dataset.validate datasets/benchmark/v0 --json <scratch>/dataset-validation.json` | 종료 0, 188 examples, 오류 0, 기존 템플릿 중복 경고 16 |
| `python -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 --baselines wlie,b1_python,b2_js,b_fixed,existing_law,mock_model --splits dev,test,adversarial_holdout --out <scratch>/waymaker-eval.json --fail-on-hard-gates wlie` | 종료 0, WLIE hard gates 통과 |
| `python ../../scripts/check_bfixed_metrics.py <scratch>/waymaker-eval.json ../../audits/mission-002-phase-1-1/comparison.json` | PASS, 엔지니어링 회귀 기준 통과 |
| `python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --check-only` | 종료 1, 학습 파일 부재로 정상 거부; 학습 미실행 |
| `PATH=/Users/seonjaekim/dev/Paradiso/.venv-check/bin:$PATH bash scripts/check_repo.sh` (저장소 루트) | PASS, 백엔드 회귀 및 지식 평가 69/69 통과 |
| `python3 artemis_bootstrap/guardrail_shadow.py evaluate_all` | 종료 0, 합성·회귀 그룹 생성, 실제 모델 그룹 없음 |

첫 전체 검사에서 CLI의 예외 형식 관련 6건이 실패했고 파서를 수정한 뒤
통과했습니다. 저장소 검증은 최초 jsdom 부재로 중단되었습니다. npm 설치도
레지스트리 시간 초과로 실패해 기존 의존성을 임시 연결한 뒤 검증을 완료했습니다.
이 실패를 모델 추론 성공이나 새 환경 설치 성공으로 보고하지 않습니다.
`python3 artemis_bootstrap/check_model_identity.py`는 305개 파일을 확인했고
위반 0건으로 통과했습니다. 역사 기록·거부 테스트·교사 정책 목록은 허용
사유를 따로 출력합니다. `.env.local` 같은 숨김 실행 설정도 검사합니다.
필수 산출물 8개와 README의 존재, 로컬 문서 링크, 보관 파일 7개의 해시,
생성 보고서 해시 및 벤치마크·검토·원장·스키마의 원본 보존을 확인했습니다.
`git diff --check`도 통과했습니다. 한국어 보고서·README·생성 섀도 보고서에
`node ~/dev/korean-language-quality/bin/kolint.mjs --genre documentation`을
실행한 결과 지적 0건·차단 0건입니다. 법률 원문은 문체 교정하지 않았습니다.

## 남은 작업과 제한

독립 MLX-VLM 환경과 충분한 자원에서 32토큰 점검을 통과해야 새 실제 기준선을
만들 수 있습니다. CUDA 학습 호환성·VRAM은 이 Mac에서 검증하지 못했습니다.
[학습 계획](WAYMAKER-ARTEMIS-FINETUNING-PLAN.md)은 E4B 원본을 대상으로 한
TRL·PEFT QLoRA, 인용 근거 지도, 데이터 격리, 어댑터 revision 관리 및 배포 전
재평가를 구분합니다. 권장 24GB GPU는 계획 추정이며 학습 성공 보장이 아닙니다.
변환본과 원본 카드의 라이선스 표기 차이도 배포 전에 해소해야 합니다.
유료 자원 사용, 새 PR, 병합, 운영 배포는 수행하지 않습니다.
