# Waymaker Artemis 모델 평가 실행 보고서 (`gemma4-e4b-recovery-preflight-20261029`)

## 1. 실행 메타데이터
- **실행 ID**: `gemma4-e4b-recovery-preflight-20261029`
- **실행 일시**: 2026-10-29T16:14:45.767939+00:00
- **평가 모드**: `candidate_eval`
- **실행 상태**: `not_executed` (사유: Insufficient disk space: 3.16 GB; need 6.0 GB; Swap pressure: 8.39 GB used; limit 2.0 GB; mlx-vlm 0.7.11 not installed (found None))
- **모델명**: `mlx-community/gemma-4-e4b-it-4bit`
- **모델 revision**: `475b9088d29754a3379866cf5aeb6b41acd313c2`
- **실행 구분 / 런타임**: `real_inference` / `mlx_vlm`
- **어댑터 유형**: `local_mlx`
- **벤치마크 파일**: `artemis_eval_dev_blind_20.json` (0문항)
- **Git Commit**: `d3e9490e22bdf455ca0bda958106811195a49d6d`

## 2. 모드 격리 및 거버넌스 원칙 준수 확인
> [!IMPORTANT]
> **Mode B (후보군 평가)**: 개발 및 홀드아웃 후보 문항에 대한 진단 목적의 루브릭 일치율입니다. 법률 전문가 승인이 완료되지 않은 문항이므로 공식 법률 골드 정확도로 인용할 수 없습니다.

## 3. 평가 요약 지표
| 지표 항목 | 측정값 | 설명 |
|:---|:---:|:---|
| **총 평가 문항** | 0건 | 실행 대상 문항 수 |
| **전체 합격 수 / 합격률** | N/A (평가 문항 없음) | 루브릭 기준 전체 합격 비율 |
| **후보군 진단 일치율 (Candidate)** | N/A (후보 문항 평가 없음) | 미검증 법률 후보군 탐색적 평가 일치율 |
| **공식 골드 정확도 (Official Gold)** | **N/A (공식 골드 검증 항목 없음 / 전 문항 사람 법률 검토 대기)** | 사람 법률 전문가 서명 완료 골드 정확도 |

### 3.1 4대 차원별 세부 합격률
| 평가 차원 | 합격률 | 설명 |
|:---|:---:|:---|

## 5. 생성 아티팩트 목록
- `run_summary.json`: 기계 판독용 전체 실행 결과 및 진단 레코드
- `error_summary.csv`: 문항별 실패 원인 및 진단 태그 요약표
- `report.md`: 본 한국어 평가 실행 보고서
- `run_manifest.json`: 실행 코드 및 데이터셋 SHA-256 매니페스트