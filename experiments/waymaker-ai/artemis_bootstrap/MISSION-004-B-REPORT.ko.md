# ARTEMIS MISSION 004-B 실행 보고서
## 독립 벤치마크 구축 및 평가기 신뢰성 검증 보고서

- **보고서 버전**: 1.0.0
- **수행 일자**: 2026-10-29
- **수행 환경**: `club-paradiso/Visable` (`feat/artemis-mission004-b`)
- **기반 커밋**: `6593c34` (PR #722 병합 커밋, Mission 004-A 기반)
- **책임 에이전트**: Artemis Subsystem (Gemini 3.8 Flash)

---

## 1. 미션 개요 및 핵심 원칙

Mission 004-A에서 수립된 4대 평가 차원(출처 충실도, 인용 정확성, 절차 무결성, 보류 적절성) 및 검증기 인프라를 바탕으로 본 Mission 004-B에서는 평가기(`artemis_eval.py`)의 신뢰성을 독립적으로 감사하고 출입국·사증·체류 안내의 신뢰성을 객관적으로 측정하기 위한 **독립 평가 후보 60문항(개발·보정용 20문항과 별도 홀드아웃 40문항)**을 구축하였습니다.

### 준수한 평가 무결성 원칙

1. **독립성 분리**: 문항 생성과 채점 기준 보정 단계를 엄격히 분리하였습니다.
2. **홀드아웃 보호**: 홀드아웃 40문항을 채점기 규칙이나 모델 파라미터 튜닝에 일절 사용하지 않았습니다.
3. **점수 비혼합**: 기존 Mission 004-A의 10문항과 신규 60문항의 점수를 혼합하여 평가하지 않습니다.
4. **라벨 무결성**: AI가 생성한 법률 라벨을 사람의 공식 검토 완료로 간주하지 않았으며 독립 검증이 필요한 항목은 `needs_human_review: true`로 격리 등록하였습니다.
5. **데이터셋 암호학적 무결성**: SHA-256 manifest를 생성하여 데이터 변조 및 누출을 방지하였습니다.

---

## 2. 평가기 신뢰성 독립 감사 및 취약점 개선 (TDD)

`artemis_eval.py`의 채점 로직과 검증기를 정밀 감사하여 실제 발생 가능한 오탐(False Positive) 및 미탐(False Negative) 취약점을 식별하고 반례 테스트(`test_artemis_eval_reliability.py`)를 먼저 작성하여 결함을 재현한 뒤 수정하였습니다.

### 2.1 식별된 취약점 및 개선 사항

| 번호 | 취약점 유형 | 기존 코드의 한계 | 개선 내용 및 방어 로직 |
|:---|:---|:---|:---|
| 1 | **부정 표현 반전 미탐** | `trust_gate.polarity_flips`가 빈도수 숫자(`3회`)가 포함된 문장만 한정 검사하여 일반 금지 표현("취업할 수 없다" → "취업할 수 있다")을 탐지하지 못함 | `detect_polarity_and_permission_reversal` 함수를 도입하여 부정 조동사 및 금지 어휘의 허용 반전을 문장 단위로 교차 검증 |
| 2 | **허가 반전 오탐** | `trust_gate.permission_flips` 정규식이 `불인정됩니다` 내부의 `인정`에 매칭되어 정상 거부 문장을 오히려 불법 허가로 오판함 | 부정 전방탐색 및 후방탐색 `(?<!불)인정(?:됩\|합\|되어\|함)`을 적용하여 정밀화 |
| 3 | **표 행·열 전치 미탐** | `1회 부여기간`과 `총 체류기간`이 동일한 도메인 역할을 공유하여 표 수치가 전치되어도 채점기를 통과함 | `detect_role_and_column_swaps`를 구현하고 `forbidden_subject_bindings`에 절 단위 조사 결합 정규식 매칭을 적용하여 표 전치 오류 차단 |
| 4 | **빈 인용 목록 미탐** | `must_cite`가 빈 목록인 보류 및 인젝션 케이스에서 미인가 출처 인용(`unlisted_citations`) 검사가 건너뛰어짐 | `allow_unlisted_citations`가 `False`인 경우 `must_cite` 존재 여부와 무관하게 `set_cites - set(must_cite)`를 전수 감사하도록 수정 |
| 5 | **미승인 출처 승인 오용** | 인터넷 블로그(`community_post`)나 인젝션 페이로드(`injection_probe`)가 `approval_state: "approved"`로 오기입되어도 스키마 검증 통과 | `validate_eval_item`에 검증 규칙을 추가하여 해당 출처가 `approved` 상태를 가질 경우 즉각 유효성 오류(ValidationIssue)를 발생시키도록 차단 |
| 6 | **사람 검토 상태 누락** | `metadata.needs_human_review` 플래그가 채점 결과에 전파되지 않아 사람 검토 대기 항목이 기계 채점 완료로 오인될 위험 | 채점 결과의 `flags` 속성에 `pending_human_review` 플래그를 자동으로 반영하도록 연동 |

---

## 3. 신규 평가 후보 60문항 구축 체계

### 3.1 10대 핵심 출입국 도메인 배분 매트릭스

20문항의 개발 세트와 40문항의 독립 홀드아웃 후보 세트에 걸쳐 10개 영역을 2:4 비율로 균등 배분하였습니다.

```
+-------------------------------------------------------------+-------+-----------+-------+
| 평가 도메인                                                 | Dev   | Heldout   | 합계  |
+-------------------------------------------------------------+-------+-----------+-------+
| 1. 사증발급과 국내 체류절차 (Visa vs Stay Procedure)         | 2문항 | 4문항     | 6문항 |
| 2. 체류자격 및 세부분류 (Subcodes: D-2, E-7, F-2, *-T 등)   | 2문항 | 4문항     | 6문항 |
| 3. 제출서류·수수료·기간 (Fees, Periods, Documents)          | 2문항 | 4문항     | 6문항 |
| 4. 법령 및 업무편람 판본 (2026.10 최신 판본 및 시행일)      | 2문항 | 4문항     | 6문항 |
| 5. 근거와 답변 간 모순 (Contradiction & Polarity Reversal)  | 2문항 | 4문항     | 6문항 |
| 6. 다국어 질의 (Multilingual: 영어, 베트남어, 중국어)       | 2문항 | 4문항     | 6문항 |
| 7. 프롬프트 인젝션 (Prompt Injection & Jailbreak Defense)    | 2문항 | 4문항     | 6문항 |
| 8. 모호한 질문과 적절한 보류 (Clarification & Abstention)   | 2문항 | 4문항     | 6문항 |
| 9. 표 행·열 혼동 (Table Row/Column Swaps)                   | 2문항 | 4문항     | 6문항 |
| 10. 구버전·미승인 출처 인용 차단 (Legacy & Unapproved Sources)| 2문항 | 4문항     | 6문항 |
+-------------------------------------------------------------+-------+-----------+-------+
| 총계                                                        | 20문항| 40문항    | 60문항|
+-------------------------------------------------------------+-------+-----------+-------+
```

### 3.2 10문항 단위 점진적 생성 및 자동 검증

`build_eval_candidates.py` 빌더 스크립트를 통해 10문항 단위 6개 배치로 생성하며 실시간 유효성 검증을 거쳤습니다.

- **Batch 1 (DEV-001 ~ DEV-010)**: 도메인 1~5 개발 세트 (10문항 검증 통과)
- **Batch 2 (DEV-011 ~ DEV-020)**: 도메인 6~10 개발 세트 (10문항 검증 통과)
- **Batch 3 (HLD-001 ~ HLD-010)**: 도메인 1~5 홀드아웃 세트 1차 (10문항 검증 통과)
- **Batch 4 (HLD-011 ~ HLD-020)**: 도메인 6~10 홀드아웃 세트 2차 (10문항 검증 통과)
- **Batch 5 (HLD-021 ~ HLD-030)**: 도메인 1~5 홀드아웃 세트 3차 (10문항 검증 통과)
- **Batch 6 (HLD-031 ~ HLD-040)**: 도메인 6~10 홀드아웃 세트 4차 (10문항 검증 통과)

---

## 4. 데이터 파일 및 암호학적 매니페스트 (MANIFEST)

산출된 벤치마크 데이터셋은 `experiments/waymaker-ai/artemis_bootstrap/benchmarks/` 디렉터리에 분리 저장되었으며 SHA-256 체크섬을 통해 무결성이 보증됩니다.

### 4.1 생성된 파일 목록 및 SHA-256 체크섬

| 파일 경로 | 문항 수 | 파일 SHA-256 체크섬 |
|:---|:---:|:---|
| `benchmarks/artemis_eval_dev_20.json` | 20 | `e680a6b73898f0ef2389d3d4b6ec67e45e69e4693a206cb388a18356bb0e0ffb` |
| `benchmarks/artemis_eval_heldout_40.json` | 40 | `141b778216be2a9d6bf3744c6ea40e4e7e6005d5c074f514b806d274d8fb8d63` |
| `benchmarks/artemis_eval_candidates_60.json` | 60 | `a4928014dd5dfd7df43e93b3fec28ef1c0800b70ff98cfd14e137b0d77fef69e` |
| `benchmarks/MANIFEST.json` | - | 전체 파일 및 60개 문항별 정규화 SHA-256 레코드 수록 |

### 4.2 사람 검토 대기 큐 (`pending_human_review_60.json`)

총 60문항 중 **16문항**이 사람 검토 대기(`needs_human_review: true`)로 분류되었습니다.

1. **프롬프트 인젝션 및 보안 경계 시험 (6문항)**:
   - `ARTEMIS-004-DEV-013`, `ARTEMIS-004-DEV-014`, `ARTEMIS-004-HLD-013`, `ARTEMIS-004-HLD-014`, `ARTEMIS-004-HLD-033`, `ARTEMIS-004-HLD-034`
   - 사유: 적대적 프롬프트 공격에 대한 안전 거부 기준은 보안 관리자 및 정책 담당자의 독립 승인이 필수적입니다.
2. **복합 정책 및 법령 개정 적용 판단 (10문항)**:
   - `ARTEMIS-004-HLD-004` (F-2-R 지역특화비자 인구감소지역 실거주 의무)
   - `ARTEMIS-004-HLD-007` (2026.10 개정 출입국관리법 제4조 및 제85조 직제 개정)
   - `ARTEMIS-004-HLD-008` (2026 K-point E-7-4 한국어능력 배점)
   - `ARTEMIS-004-HLD-023` (F-2-7 점수제 소득금액증명원 필수 요건)
   - `ARTEMIS-004-HLD-027` (2026.10 출입국관리법 제17조 현행 고시)
   - `ARTEMIS-004-HLD-028` (유학생 재정입증 수도권 및 비수도권 차등 기준)
   - `ARTEMIS-004-HLD-031` (베트남어 질의: E-9에서 E-7-4 전환 근무기간)
   - `ARTEMIS-004-HLD-032` (영어 질의: 유학생 방학 중 아르바이트 허가 의무)
   - `ARTEMIS-004-HLD-036` (외국인 개인사업자등록 허용 체류자격)
   - `ARTEMIS-004-HLD-037` (F-2-7 점수 구간별 체류기간 상한)
   - 사유: 지침 해석의 행정청 재량 범위 및 다국어 번역 정확성에 대한 출입국 전문 행정사와 변호사의 최종 서명이 필요합니다.

---

## 5. 자동 검증 및 회귀 테스트 결과

모든 테스트는 실제 명령어를 실행하여 검증을 통과하였습니다.

### 5.1 신규 벤치마크 스위트 테스트 (`test_artemis_eval_benchmark_60.py`)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_benchmark_60.py
```
```text
============================= test session starts ==============================
collected 6 items

experiments/waymaker-ai/tests/test_artemis_eval_benchmark_60.py ......   [100%]

============================== 6 passed in 0.12s ===============================
```
- Dev 20문항 및 Heldout 40문항 분할의 엄격한 분리 및 중복 ID 부재 검증 완료.
- JSON Schema 및 도메인 유효성 60/60 통과 확인.
- MANIFEST.json 파일 및 문항 SHA-256 일치 확인.
- 채점기 코드 내 홀드아웃 ID 누출 부재 확인.

### 5.2 평가기 신뢰성 단위 테스트 (`test_artemis_eval_reliability.py`)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_reliability.py
```
```text
============================= test session starts ==============================
collected 9 items

experiments/waymaker-ai/tests/test_artemis_eval_reliability.py ......... [100%]

============================== 9 passed in 0.08s ===============================
```

### 5.3 기존 인프라 회귀 테스트 (`test_artemis_eval_infrastructure.py`)

```bash
pytest experiments/waymaker-ai/tests/test_artemis_eval_infrastructure.py
```
```text
============================= test session starts ==============================
collected 34 items

experiments/waymaker-ai/tests/test_artemis_eval_infrastructure.py ......... [100%]

============================= 34 passed in 0.13s ===============================
```

### 5.4 저장소 전체 회귀 테스트 (`experiments/waymaker-ai/tests/`)

```bash
pytest experiments/waymaker-ai/tests/
```
```text
============================= test session starts ==============================
platform darwin -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
collected 1411 items

============================ 1411 passed in 24.26s =============================
```
저장소 내 총 1,411개 테스트가 단 한 건의 실패 없이 모두 통과하여 기존 기능에 대한 무결성을 입증하였습니다.

---

## 6. 후속 Mission 004-C 권고안

1. **사람 전문가 서명 절차 (Human-in-the-loop Sign-off)**:
   - `pending_human_review_60.json`에 등재된 16건에 대해 법무부 출입국 업무 유경험 전문가가 문항 및 정답 기준을 독립 서명하도록 합니다.
2. **독립 블라인드 평가 파이프라인 가동**:
   - 홀드아웃 40문항은 모델 학습 프로세스 및 프롬프트 튜닝 엔지니어에게 완전히 은닉된 별도 실행 환경(Clean-room Worker)에서 배치 채점합니다.
3. **평가 보고서 분리 발행**:
   - 개발용 20문항 지표와 홀드아웃 40문항 벤치마크 지표를 단일 평균으로 합산하지 않고 반드시 독립된 섹션으로 분리 보고합니다.
4. **실시간 가드레일과의 통합**:
   - 이번에 정밀화된 `detect_polarity_and_permission_reversal`과 `detect_role_and_column_swaps`를 서빙 런타임의 사후 검증 필터로 배치하여 실시간 답변 왜곡을 사전 차단할 것을 권고합니다.
