# ARTEMIS 모델 평가 실행 보고서 (`artemis_run_20261029_075205_d79aea`)

## 1. 실행 메타데이터
- **실행 ID**: `artemis_run_20261029_075205_d79aea`
- **실행 일시**: 2026-10-29T07:52:05.886131+00:00
- **평가 모드**: `candidate_eval`
- **실행 상태**: `completed`
- **모델명**: `recorded_recorded_responses_dev_20`
- **어댑터 유형**: `recorded`
- **벤치마크 파일**: `artemis_eval_dev_20.json` (20문항)
- **Git Commit**: `0ade4ad3fc9295e05de0e30f38cb060142c6fa39`

## 2. 모드 격리 및 거버넌스 원칙 준수 확인
> [!IMPORTANT]
> **Mode B (후보군 평가)**: 개발 및 홀드아웃 후보 문항에 대한 진단 목적의 루브릭 일치율입니다. 법률 전문가 승인이 완료되지 않은 문항이므로 공식 법률 골드 정확도로 인용할 수 없습니다.

## 3. 평가 요약 지표
| 지표 항목 | 측정값 | 설명 |
|:---|:---:|:---|
| **총 평가 문항** | 20건 | 실행 대상 문항 수 |
| **전체 합격 수 / 합격률** | 18건 (90.0%) | 루브릭 기준 전체 합격 비율 |
| **후보군 진단 일치율 (Candidate)** | 90.0% (18/20) | 미검증 법률 후보군 탐색적 평가 일치율 |
| **공식 골드 정확도 (Official Gold)** | **N/A (공식 골드 검증 항목 없음 / 전 문항 사람 법률 검토 대기)** | 사람 법률 전문가 서명 완료 골드 정확도 |

### 3.1 4대 차원별 세부 합격률
| 평가 차원 | 합격률 | 설명 |
|:---|:---:|:---|
| `source_fidelity` | 100.0% | 출처 충실도 (사실 왜곡 및 수치 전치 방지) |
| `citation_accuracy` | 90.0% | 인용 정확성 (필수 인용 및 미승인 출처 차단) |
| `procedural_integrity` | 100.0% | 절차 무결성 (사증-체류 절차 분리 및 되묻기) |
| `abstention_appropriateness` | 100.0% | 보류 적절성 (부적절한 침묵 방지 및 인젝션 방어) |

## 4. 진단 오류 및 불일치 상세 분석 (Diagnostic Breakdown)
| 오류 분류 코드 | 발생 건수 | 설명 |
|:---|:---:|:---|
| `unknown_failure` | 4건 | 기타 오류 (General Failure) |
| `unlisted_citations` | 2건 | 미승인/미인가 출처 인용 (Unlisted/Unapproved Citations) |

## 5. 생성 아티팩트 목록
- `run_summary.json`: 기계 판독용 전체 실행 결과 및 진단 레코드
- `error_summary.csv`: 문항별 실패 원인 및 진단 태그 요약표
- `report.md`: 본 한국어 평가 실행 보고서
- `run_manifest.json`: 실행 코드 및 데이터셋 SHA-256 매니페스트