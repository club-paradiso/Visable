# Waymaker Artemis — PR #726 추가 감사 수정

작성일: 2026-10-30. 감사 기준: `f038dadf5b08ffccd430b139ff725e07bd0d4da0`.
작업 브랜치: `feat/artemis-mission005-a`. 기존 PR의 Draft 상태를 유지합니다.
**Gemma 4 E4B inference = not_executed, Official Gold Accuracy = N/A**입니다.

## 발견사항과 수정

| 발견사항 | 원인 | 수정 및 검증 |
|---|---|---|
| P1 추론 입력 누출 | `source` 객체 전체가 프롬프트로 전달됨 | 공통 허용 목록으로 증거를 투영하고 러너→worker 경계와 프롬프트 생성 시 다시 적용. `SECRET_ANSWER` 중첩 삽입·러너 통합 검사 통과 |
| P1 독립 격리 과장 | 단순 투영 manifest가 air-gapped로 표시됨 | `blind_projection_only`, `isolation_not_verified`, `clean_room_verified: false`로 정정. 요구 증거와 상태 전이를 공통 정책에 명시 |
| P2 오염 검사 오판 | 코퍼스가 비었거나 토큰이 없어도 clean 반환 | `unknown`·점수 `null` 도입. 코퍼스 ID·해시, 비교 범위·분석 문서 수·휴리스틱 한계를 구조화 보고서에 기록 |
| P2 체크포인트 무결성 부족 | tokenizer는 존재, shard는 크기만 확인 | 고정 revision의 신뢰 가능한 해시 기준을 정책에 고정하고 tokenizer·인덱스·모든 shard를 스트리밍 검증. 같은 크기의 손상도 거부 |

`waymaker_ai/inference_input.py`는 증거의 `id`, `title`, `text`를 그대로
유지합니다. 출처는 문서·판본 식별자, 조항, 날짜, URL, 영역, 출처 종류,
페이지처럼 명시한 스칼라 필드만 남깁니다. `review_note`, 정답·루브릭,
승인·검토자 표시, 임의 필드와 허용 필드에 위장한 중첩 객체는 전달하지
않습니다. 본문에 있는 법률 문구를 정규식으로 지우거나 다시 쓰지 않습니다.
잘못된 본문·제목 객체는 문자열로 변환하지 않고 거부합니다.

이 투영은 LocalModelAdapter의 subprocess 요청, worker의 최종 메시지,
smoke 메시지, 평가 격리의 증거 투영에서 공유합니다. 채점기는 원본 항목을
계속 사용하므로 검토·정답 정보가 채점 자료에서 사라지지는 않습니다.
생성 manifest에는 새 입력 투영 코드의 해시도 기록합니다.

연구용 `flip_judge.load_e4b()`에 남아 있던 직접 로딩 경로도 공통 E4B
무결성·런타임·자원 검사로 연결했습니다. 문자열 질문만 투영하며 누락된
런타임에서는 ML 라이브러리 로딩 전에 `not_executed` 사유로 거부합니다.
새 judge 캐시 키에는 모델 출처 정보를 포함해 과거 캐시를 재사용하지
않습니다. 기존 캐시 파일과 실험 결과는 수정하지 않았습니다. 이 경로의
실제 모델 로딩·생성 성공은 아직 검증하지 못했습니다.

## 격리와 오염 검사의 의미

새 독립 벤치마크도 외부 접근 통제 증거가 없으면 검증되지 않은 상태입니다.
작성자 선언과 역할 정책은 입력·설계 규격이며 신원 인증이나 OS 접근 통제가
아닙니다. 해시는 내용 일치만 확인합니다. 격리 검증에는 외부에서 강제하는
신원·ACL, 개발자·러너의 정답 키 접근 거부 실험, 독립 키 관리와 격리 채점기,
실행 ID·파티션 해시에 연결된 접근 로그 및 인증된 독립 감사가 필요합니다.
유효기간과 철회·누출 대응도 요구합니다. 현재 신뢰할 수 있는 외부 검증기가
없어 로컬 호출로 `isolation_verified` 상태를 만들 수 없습니다.

향후 검증기가 도입되어도 권한 변경, 증거 만료·철회 또는 누출이 발견되면
`isolation_not_verified`로 되돌려야 합니다. 기존 40건은 저장소에서 정답에
접근할 수 있었으므로 독립 미공개 평가로 인정하지 않습니다.

오염 검사의 clean은 제공한 비교 코퍼스에서 큰 어휘 중복이 발견되지
않았다는 뜻입니다. 분석할 수 없는 입력은 unknown입니다. 공개되지 않은
학습 코퍼스, 의미가 같은 의역, 법령 공통 문구 때문에 생기는 오탐·누락을
해결하지 못하며 법률 정확성이나 독립성을 인증하지 않습니다. 기존 tuple
API도 unknown과 `None` 점수를 반환합니다. 감사 기록에는
`check_item_report()`의 전체 출처·범위 필드를 보존해야 합니다.

## 실제 체크포인트 검사

추론 revision은 `475b9088d29754a3379866cf5aeb6b41acd313c2`를 유지합니다.
Hugging Face의 같은 revision API에서 LFS SHA-256과 크기를 얻었습니다.
작은 가중치 인덱스만 원격에서 읽고 Git blob ID를 대조한 뒤 SHA-256을
계산했습니다. 모델 가중치는 새로 다운로드하지 않았습니다.

```bash
python3 artemis_bootstrap/verify_checkpoint.py \
  --out artemis_bootstrap/runs/post-audit-20261030/checkpoint_sha256_verification.json
```

종료 0, `status: verified`입니다. tokenizer·인덱스·가중치 전체를 1 MiB씩
읽어 확인했습니다. 메타데이터 검증과 전체 무결성 검증은 별도 필드입니다.
누락된 기준 해시, 신뢰 목록과 다른 shard, 손상된 파일은 거부합니다.
메타데이터만 검증한 과거 기록은 새 실제 추론 출처 검사에서 거부합니다.

같은 프로세스의 반복 읽기는 경로·device·inode·크기·mtime·ctime에 연결된
캐시를 사용합니다. 파일 식별 정보가 바뀌거나 프로세스가 새로 시작되면
다시 계산합니다. 악의적인 커널·파일시스템이나 정책 파일 자체의 위조까지
막는 인증 체계는 아닙니다. 신뢰 기준은 고정된 Hub 자료와 검토된 정책입니다.
E2B는 원격 기준 해시만 기록했으며 로컬 가중치 전체 검증이나 추론은
수행하지 않았습니다.

새 사전 점검도 실행했습니다. 실제 모델 생성은 **MLX-VLM 0.7.11 미설치**로
실행되지 않았습니다. 이전 보고서의 디스크·스왑 관측은 당시 기록으로
보존하며 현재 상태로 재사용하지 않습니다.

증거: [SHA-256 검사](runs/post-audit-20261030/checkpoint_sha256_verification.json),
[원격 해시 기준](runs/post-audit-20261030/trusted_file_references.json),
[현재 추론 사전 점검](runs/post-audit-20261030/inference_preflight.json).
기준 형식: [Hub API 문서](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api),
[Git 객체 해시 문서](https://git-scm.com/docs/git-hash-object).

## 테스트와 전체 변경 검토

수정 전 새 재현 테스트 15건이 모두 실패했습니다. 추가로 연구용 로더의
사전 검사 우회, 과거 judge 캐시 재사용, 메타데이터만으로 실제 추론 기록을
인정하는 결함도 각각 실패 테스트로 확인한 후 수정했습니다. 스트리밍 읽기,
Git 객체 헤더, 신뢰 목록에 없는 shard 검사도 추가했습니다. 기존 테스트를
삭제하거나 약화하지 않았습니다.

| 실행한 검사 | 결과 |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests` | 1,551 passed, 26.47초. 기존 1,530건 포함 |
| `python -m pytest -q -p no:cacheprovider tests/test_post_audit_hardening.py tests/test_artemis_runner.py tests/test_artemis_foundation.py` | 최종 대상 검사 60 passed, 0.58초 |
| `PATH=/Users/seonjaekim/dev/Paradiso/.venv-check/bin:$PATH bash scripts/check_repo.sh` | 종료 0, 백엔드 회귀 및 지식 평가 69/69 통과 |
| `python -m waymaker_ai.dataset.validate datasets/benchmark/v0 --json <scratch>/dataset-validation.json` | 종료 0, 188 examples, 오류 0, 기존 중복 경고 16 |
| CI와 같은 6개 baseline·3개 split 오프라인 평가 및 `check_bfixed_metrics.py` | WLIE hard gate·B-fixed 엔지니어링 회귀 기준 통과. 법률·배포 승인은 별도 |
| `python3 artemis_bootstrap/check_model_identity.py` | PASS, 312개 파일, 위반 0건 |
| `git diff --check` 및 한국어 문서 lint | 통과, lint 지적·차단 0건 |

추론 사전 점검은 `experiments/waymaker-ai`에서 다음 명령으로 실행했고 종료
코드는 3입니다. 가중치 로딩·생성은 없습니다.

```bash
python3 artemis_bootstrap/probe_gemma4.py \
  --python /Users/seonjaekim/dev/Visable-artemis/experiments/waymaker-ai/artemis_bootstrap/.venv/bin/python \
  --out artemis_bootstrap/runs/post-audit-20261030/inference_preflight.json
```

테스트용 Python은 기존 `/Users/seonjaekim/dev/Paradiso/.venv-check/bin/python`을
사용했습니다. 저장소 검사에 필요한 기존 Node 의존성을 임시 심볼릭 링크로
읽고 링크만 제거했습니다. 해당 워크트리의 파일·패키지는 변경하지 않았습니다.

감사 기준 PR의 **78개 변경 경로 전체**를 검토했습니다. 소스 차이와 호출
경로를 읽고, 생성 자료는 모든 레코드의 구조·모델 출처·상태·해시를 확인했습니다.
러너, worker, 입력 투영, 격리·오염 검사, 무결성·모델 정책, 채점·골드 제한,
섀도 평가와 학습 게이트는 집중 검토했습니다. 16개 패킷은 기존 필드와
unreviewed 상태가 보존되고 audit_dossier만 추가됐음을 확인했습니다.
자료의 법률 내용 자체를 독립적으로 재검증했다는 뜻은 아닙니다.
경로별 범위와 기준 해시는 [검토 명세](PR-726-REVIEW-COVERAGE.json)에 있습니다.

이전 실행 파일·벤치마크·40건 홀드아웃·법률 검토 자료·외부 캐시는 기준
커밋과 같은 바이트를 유지합니다. 새 증거는 별도 실행 디렉터리에 기록했습니다.
기준 커밋의 두 GitHub Actions는 success로 완료됐음을 확인했습니다. 추가
수정의 원격 결과는 기존 PR의 최종 head Checks와 작업 최종 보고서에서 확인합니다.

## 남은 위험과 병합 판단

네 감사 결함의 코드 수정과 로컬 검증은 완료했습니다. 최종 head의 필수 CI가
통과하면 이번 소프트웨어 수정은 병합 검토가 가능합니다. 요청에 따라 Draft를
유지하고 실제 병합은 수행하지 않습니다. 실제 E4B 추론·CUDA 학습·독립적인
접근 통제 검증과 사람 법률 검토는 여전히 완료되지 않았습니다. 법률 자료는
AI 조사·검토 후보이며, 원본·변환본의 라이선스 표기 차이도 남아 있습니다.
이 PR의 코드 병합이 법률 성능 인증이나 운영 배포 승인을 뜻하지 않습니다.
