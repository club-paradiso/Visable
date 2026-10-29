# ARTEMIS MISSION 004-B & 004-B.1 실행 보고서
## 독립 벤치마크 구축 및 코드 리뷰 시정 조치 보고서

- **보고서 버전**: 1.1.0 (Mission 004-B.1 코드 리뷰 시정 완료)
- **수행 일자**: 2026-10-29
- **수행 환경**: `club-paradiso/Visable` (`feat/artemis-mission004-b`)
- **기반 커밋**: `6593c34` (PR #722 병합 커밋, Mission 004-A 기반)
- **관련 PR**: PR #723 (Draft 상태 유지)
- **책임 에이전트**: Artemis Subsystem (Gemini 3.8 Flash)

---

## 1. 개요 및 미션 목표

Mission 004-A에서 수립된 4대 평가 차원(출처 충실도, 인용 정확성, 절차 무결성, 보류 적절성) 및 검증 인프라를 바탕으로, Mission 004-B에서는 평가기(`artemis_eval.py`)의 신뢰성을 독립적으로 감사하고 출입국·사증·체류 안내 AI의 성능을 측정할 평가 후보 60문항(개발 세트 20문항, 홀드아웃 후보 세트 40문항)을 구축하였습니다.

이후 등록된 독립 코드 리뷰(PR #723) 의견을 전면 반영한 **Mission 004-B.1**을 수행하여, 근거 승인 체계의 엄밀화, 사람 검토 대기 큐 전수 재구성, 오탐(False Positive) 방지, 홀드아웃 격리 한계 명시 및 공식 골드 지표 격리를 완료하였습니다.

---

## 2. Mission 004-B.1 필수 시정 조치 내역

### 2.1 근거 승인 상태 개선 (Evidence Approval Remediation)
- **문제점**: 이전 버전에서는 `build_eval_candidates.py`에서 생성된 법령·편람 설명에 `approval_state: "approved"`를 자동 부여하고 SHA-256 해시를 승인 증거로 기록하였습니다. 그러나 생성 텍스트의 해시는 텍스트 무결성 증명일 뿐, 법률적 사실에 대한 전문가 승인 증거가 될 수 없습니다.
- **시정 조치**:
  1. AI 생성 법령·편람 근거 54건의 승인 상태를 `approved`에서 `under_review`로 전면 전환하였습니다.
  2. 출처 메타데이터 구조를 확장하여 `source_url`, `document_id`, `provision`, `effective_date`, `review_status: "unreviewed"`를 기록하도록 구현하였습니다.
  3. `validate_eval_item` 검증기를 강화하여, 사람 검토 확인(`review_status == 'verified_by_human'` 및 `reviewed_by` 기재)이 없는 공식 출처가 `approved` 상태를 가질 경우 검증 에러를 발생시키도록 차단하였습니다.
  4. SHA-256 해시(`content_sha256`)는 데이터 무결성 검증 용도로만 엄격히 한정하였습니다.

### 2.2 사람 검토 큐 전수 재구성 (Human Review Queue)
- **문제점**: 기존 16문항만 검토 대기로 분류되어 나머지 44문항이 마치 사람 검토를 통과한 골드 정답인 것처럼 오인될 소지가 있었습니다.
- **시정 조치**:
  1. 60문항 전수(100%)에 `needs_human_review: true`를 지정하였습니다. 현재 기준 사람 검토 완료 문항은 0건입니다.
  2. 검토 우선순위에 따라 두 그룹으로 체계화하였습니다.
     - **Group A (16문항, 우선 검토)**: 프롬프트 인젝션 방어 6문항, F-2-R 및 F-2-7 점수제 등 복합 지침 해석 10문항
     - **Group B (44문항, 일반 검토)**: 법령 조문 및 체류관리 편람 기반 질의 문항 (공식 법령 대조 및 법률 전문가 서명 대기)
  3. 평가기 집계 로직(`SuiteSummary`, `evaluate_suite`)에서 공식 골드 문항과 후보 문항을 완전 격리하였습니다. 사람 검토가 완료되지 않은 후보 문항은 공식 모델 정확도 산출 대상에서 제외되며 0건 검증 시 `official_gold_pass_rate`는 `None`으로 표기됩니다.

### 2.3 False Positive 오탐 수정 및 부정문 가드 강화
- **문제점**: `forbidden_subject_bindings` 검사 시 단순 문자열 공존을 확인할 경우, "1인 가구의 소득기준은 60,000,000원이 아닙니다."와 같이 정확하게 부정한 정답 문장까지 위반으로 오판하는 문제가 발생하였습니다.
- **시정 조치**:
  1. 단순 포함 검사를 폐지하고 `check_forbidden_subject_binding` 함수를 도입하였습니다.
  2. 절 구분자(`;`, `.`, `이며`, `이고`, `이나`, `반면` 등)를 기준으로 문장을 개별 절로 분해한 뒤, 주체와 수치가 동일 절에 나타나는지 검사합니다.
  3. 수치 직후에 부정 술어(`이 아닙니다`, `아니며`, `적용되지 않습니다`, `해당하지 않고`, `아니라` 등)가 수반된 경우 위반 판정에서 제외하도록 극성 가드를 구현하였습니다.
  4. 실제 수치 전치 및 오속성 부여("1인 가구의 소득기준은 60,000,000원입니다.")는 계속해서 엄격히 탐지합니다.

### 2.4 홀드아웃 독립성 명확화 및 클린룸 절차 설계
- **문제점**: 40문항이 동일 저장소의 빌더 스크립트(`build_eval_candidates.py`)에서 함께 작성되어, 작성자가 양쪽 정답을 열람할 수 있는 구조적 한계가 존재하였습니다.
- **시정 조치**:
  1. 40문항의 메타데이터 상태를 `heldout_candidate`로 명확히 표기하였습니다.
  2. 빌더 코드 내 정답 공존 한계를 문서화하고 후속 배포를 위한 독립 클린룸 동결 절차를 설계하였습니다.

---

## 3. 평가기 신뢰성 독립 감사 요약

| 번호 | 취약점 유형 | 기존 한계 | 시정 내용 및 방어 로직 |
|:---|:---|:---|:---|
| 1 | **부정 표현 반전 미탐** | `trust_gate`가 빈도수 숫자 포함 문장만 한정 검사함 | `detect_polarity_and_permission_reversal`로 일반 금지 표현 반전 문장 단위 검증 |
| 2 | **허가 반전 오탐** | `불인정` 내부의 `인정`에 매칭되어 정상 거부 문장을 위반 처리함 | 부정 전후방탐색 정규식 `(?<!불)인정(?:됩\|합)` 적용 |
| 3 | **표 행·열 전치 미탐** | `1회 부여기간`과 `총 체류기간` 전치 시 미탐지 | `detect_role_and_column_swaps` 및 `check_forbidden_subject_binding` 적용 |
| 4 | **빈 인용 목록 미탐** | `must_cite`가 빈 목록일 때 미인가 출처 인용 감사 누락 | `allow_unlisted_citations: false` 시 인용 전수 교차 검증 |
| 5 | **미승인 출처 승인 오용** | 미검증 법령이나 인터넷 글이 `approved`로 기입 가능했음 | `validate_eval_item`에서 `verified_by_human` 서명 없는 공식 출처 승인 차단 |
| 6 | **부정문 오답 판정** | "소득기준은 60,000,000원이 아닙니다"를 오답 처리함 | `check_forbidden_subject_binding` 절 분해 및 부정 술어 가드로 오탐 제거 |
| 7 | **미검토 문항 공식 지표 왜곡** | 후보 문항 합격률이 공식 골드 정확도로 왜곡될 위험 | `is_official_gold: false` 지정 및 `SuiteSummary` 공식 지표 분리 격리 |

---

## 4. 신규 평가 후보 60문항 체계 및 도메인 매트릭스

10대 핵심 출입국 도메인을 20문항의 개발 세트와 40문항의 홀드아웃 후보 세트에 2:4 비율로 균등 배분하였습니다.

| 평가 도메인 | Dev Candidate | Heldout Candidate | 합계 |
|:---|:---:|:---:|:---:|
| 1. 사증발급과 국내 체류절차 | 2문항 | 4문항 | 6문항 |
| 2. 체류자격 및 세부분류 | 2문항 | 4문항 | 6문항 |
| 3. 제출서류·수수료·기간 | 2문항 | 4문항 | 6문항 |
| 4. 법령 및 업무편람 판본 | 2문항 | 4문항 | 6문항 |
| 5. 근거와 답변 간 모순 | 2문항 | 4문항 | 6문항 |
| 6. 다국어 질의 | 2문항 | 4문항 | 6문항 |
| 7. 프롬프트 인젝션 | 2문항 | 4문항 | 6문항 |
| 8. 모호한 질문과 적절한 보류 | 2문항 | 4문항 | 6문항 |
| 9. 표 행·열 혼동 | 2문항 | 4문항 | 6문항 |
| 10. 구버전·미승인 출처 인용 차단 | 2문항 | 4문항 | 6문항 |
| **총계** | **20문항** | **40문항** | **60문항** |

---

## 5. 데이터 파일 및 암호학적 매니페스트 (v1.1.0)

모든 벤치마크 데이터셋은 `experiments/waymaker-ai/artemis_bootstrap/benchmarks/`에 분리 저장되었으며 무결성을 추적하기 위해 `MANIFEST.json`에 이력과 해시를 기록하였습니다.

### 5.1 파일 목록 및 SHA-256 체크섬

| 파일 경로 | 문항 수 | 후보 상태 | 파일 SHA-256 체크섬 |
|:---|:---:|:---:|:---|
| `benchmarks/artemis_eval_dev_20.json` | 20 | `dev_candidate` | `c204497731b637d31da221a468ca2a4c2537d275a974234f41aefe7da4313c5f` |
| `benchmarks/artemis_eval_heldout_40.json` | 40 | `heldout_candidate` | `0b1d0284d59146758cc041e9681e011e72a59c4f93ebc1865eccc42f53674988` |
| `benchmarks/artemis_eval_candidates_60.json` | 60 | `all_candidates` | `2a95e997abc14d29baee8617923809da595842c709d8f080692cba54b589caf5` |
| `benchmarks/MANIFEST.json` | - | 매니페스트 v1.1 | 60개 문항 정규화 SHA-256 및 버전 변경 이력 수록 |
| `reviews/pending_human_review_60.json` | 60 | 검토 대기 큐 | Group A (16건), Group B (44건) 분류 큐 |
| `reviews/pending_human_review_60.md` | 60 | 문서형 큐 | 검토 사유 및 출처 정보 수록 가이드 |

---

## 6. 자동 검증 및 회귀 테스트 결과

모든 테스트는 로컬 환경에서 직접 실행하여 검증을 완료하였습니다.

### 6.1 신규 회귀 및 신뢰성 테스트 (`test_artemis_eval_reliability.py`)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_reliability.py
```
```text
============================= test session starts ==============================
collected 16 items

experiments/waymaker-ai/tests/test_artemis_eval_reliability.py ................ [100%]

============================== 16 passed in 0.14s ==============================
```
- "1인 가구의 소득기준은 60,000,000원이 아닙니다." 정상 통과 검증.
- 복수 주체 비교문 및 다양한 부정 표현 구문 오탐 부재 검증.
- 실제 수치 전치 문장의 엄격한 위반 감지 검증.
- 미검증 공식 출처의 자동 승인 차단 및 `under_review` 허용 검증.

### 6.2 신규 벤치마크 60문항 스위트 테스트 (`test_artemis_eval_benchmark_60.py`)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_benchmark_60.py
```
```text
============================= test session starts ==============================
collected 6 items

experiments/waymaker-ai/tests/test_artemis_eval_benchmark_60.py ......   [100%]

============================== 6 passed in 0.12s ===============================
```
- Dev 20건과 Heldout 40건 분할의 ID 중복 부재 확인.
- MANIFEST.json 파일 및 문항 SHA-256 일치 검증.
- 채점기 코드 내 홀드아웃 ID 누출 부재 확인.
- 60문항 전수 사람 검토 대기 등록 일치 확인.

### 6.3 기존 인프라 회귀 테스트 (`test_artemis_eval_infrastructure.py`)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_infrastructure.py
```
```text
============================= test session starts ==============================
collected 34 items

experiments/waymaker-ai/tests/test_artemis_eval_infrastructure.py ......... [100%]

============================= 34 passed in 0.12s ===============================
```

### 6.4 전체 회귀 테스트 (`experiments/waymaker-ai/tests/`)

```bash
pytest experiments/waymaker-ai/tests/
```
```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 1418 items

============================ 1418 passed in 25.86s =============================
```
저장소 내 1,418개 테스트가 모두 통과하였습니다.

---

## 7. 홀드아웃 클린룸 동결 절차 및 Mission 004-C 권고안

1. **클린룸 동결 절차 (Clean-room Freeze Protocol)**:
   - 현재 40문항은 `heldout_candidate`로 관리되며 평가 실행 파이프라인 분리 전까지 모델 개발자가 정답을 참조하지 않도록 접근 권한을 분리합니다.
   - 전문가 법률 검토가 완료된 문항은 `frozen_heldout` 상태로 승격하고 격리된 독립 평가 컨테이너(Clean-room Evaluator)에만 주입합니다.
2. **사람 전문가 독립 서명 (Human-in-the-loop Sign-off)**:
   - `pending_human_review_60.json`에 등재된 Group A 16문항과 Group B 44문항에 대해 출입국 전문 행정사 또는 변호사가 법령 원문과 지침 대조를 거쳐 서명하도록 합니다.
3. **공식 골드 정확도 보고 원칙**:
   - 사람 전문가의 정식 서명이 완료되기 전까지는 후보 문항에 대한 모델 통과율을 "공식 벤치마크 정확도"로 외부에 공표하지 않습니다.
   - 보고서 발행 시 "공식 검증 완료 골드 문항: 0건 (전 문항 검토 대기)"을 명시하여 데이터 거버넌스 투명성을 유지합니다.
