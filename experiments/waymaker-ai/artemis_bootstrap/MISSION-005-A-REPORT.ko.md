# ARTEMIS MISSION 005-A 완결 보고서
## 실제 로컬 추론 베이스라인 수립, 1차 법률 증거 감사 및 평가 체계 고도화

- **작성일**: 2026-10-29
- **저장소**: `club-paradiso/Visable`
- **작업 브랜치**: `feat/artemis-mission005-a`
- **기준 커밋**: `a17233450e4b12948d35876a86cd05e588de3fce` (PR #725 머지 기준점)
- **문서 상태**: 공식 완결 보고서

---

## 1. 개요 및 핵심 성과 요약

Artemis Mission 004 시리즈(004-A ~ 004-D)에서 구축된 평가 및 검토 기반을 바탕으로, Mission 005-A에서는 소프트웨어 시제품 단계에서 벗어나 **실제 로컬 AI 모델의 추론 실행력 검증**, **Group A 16개 핵심 검토 패킷의 1차 공인 출처 대조 감사**, **법령·지침의 시간 경과에 따른 판본 관리(Versioning) 엔진 구축**, **평가 루브릭의 허위 신뢰(False Confidence) 차단을 위한 대조군 평가**, **외부 법률 전문가 온보딩 체계 마련**, **100문항 독립 블라인드 평가 접수 인프라 구축**, 그리고 **8대 섀도 가드레일 다면 확장 평가**를 완수하였습니다.

### 주요 정량 성과 지표 요약
1. **전체 소프트웨어 테스트 스위트 통과**: **1,504건 통과 / 0건 실패** (회귀 및 신규 모듈 100% 검증 완료)
2. **실제 로컬 모델 추론 실행**: Apple M1 (8GB 통합 메모리) 상에서 4-bit 양자화 모델(`gemma-3-270m-it-4bit`)을 로드하여 20개 개발 후보군 전체의 실제 추론 벤치마크 완료 (`run_real_local_mlx_dev20`)
3. **Group A 법률 증거 감사 완료**: 16건 전수의 국가법령정보센터/하이코리아/업무편람 1차 출처 대조 완료 (`source_located`: 12건, `excerpt_mismatch`: 3건, `version_mismatch`: 1건)
4. **8대 섀도 가드레일 다면 검증**:
   - 기존 7건 캘리브레이션 픽스처: 정밀도 100.0%, 재현율 100.0%, 평균 지연시간 0.04ms
   - 신규 14건 적대적 회귀 케이스: 정밀도 100.0%, 재현율 85.7%, 한국어 복합 조건문 오탐 0건
   - 실제 모델 추론 20건 출력물 평가 분리 보고 완료

---

## 2. 작업 영역별 세부 구현 및 정량 검증

### Workstream A: 실제 모델 로컬 추론 준비도 및 벤치마크 (Real Inference Baseline)
- **로컬 하드웨어 및 런타임 환경 실측**:
  - 하드웨어: Apple Silicon M1 (ARM64, 8GB 통합 메모리)
  - 가용 디스크 용량: 약 5.0 GB (대형 가중치 신규 다운로드가 제한적인 환경)
  - 사전 설치 자원: HuggingFace Hub 오프라인 캐시 내 MLX 4-bit 양자화 가중치 2종 기보유
    1. `mlx-community/gemma-4-e4b-it-4bit` (4.8GB, 4B 매개변수)
    2. `mlx-community/gemma-3-270m-it-4bit` (144MB, 270M 매개변수)
- **어댑터 고도화 (`LocalModelAdapter`)**:
  - `artemis_runner.py`의 `LocalModelAdapter`를 개선하여 HuggingFace Hub 하위 디렉터리(`hub/models--...`) 구조 자동 탐색 지원.
  - Python 환경 분리 호환성: MLX 라이브러리가 설치된 로컬 가상환경을 자동 감지하여 인프로세스 또는 경량 서브프로세스 격리 방식으로 안전 구동.
  - 리소스 보호: 8GB 메모리 제약 하에서 메모리 초과(OOM) 및 스왑 쓰레싱을 방지하도록 4.5GB 메모리 상한 준수.
- **실제 모델 추론 벤치마크 실행 (`run_real_local_mlx_dev20`)**:
  - 대상: 개발 블라인드 20문항 (`artemis_eval_dev_blind_20.json`)
  - 모델: `mlx-community/gemma-3-270m-it-4bit` (오프라인 캐시 가중치)
  - 프로세스 최대 메모리(Peak RSS): **426.7 MB** (안전 범위 4.5GB 이내 유지)
  - 평균 추론 지연시간: 문항당 약 **1.2초** (생성 속도: 약 110~140 tokens/sec)
  - **후보군 진단 일치율**: **0.0% (0/20 통과)**
  - **실제 모델의 한국어 출입국 법률 질의 적합성 실측 결론**:
    - 270M 소형 모델은 "B-2 관광 무사증 입국자도 출입국청에서 바로 D-2로 변경 가능"과 같은 치명적 극성 반전 오류(출입국관리법 제24조 위반) 및 무의미한 단어 반복("소득 소득 확인")을 생성하여, 단독으로는 한국 법률 질의에 전혀 적합하지 않음을 실증적으로 확인하였습니다.
    - 4B 모델(`gemma-4-e4b-it-4bit`)은 M1 8GB 환경에서 32토큰 생성에 약 114초가 소요되어 실시간 평가에 비현실적인 지연을 보였습니다.
    - 따라서 엄격한 검색 증강(RAG)과 독립 법률 가드레일 계층의 필수성이 경험적으로 입증되었습니다.

### Workstream B: Group A 우선순위 패킷 1차 법률 증거 감사 (Legal Evidence Audit)
- **감사 대상**: Mission 004-D에서 생성된 Group A 16개 우선순위 검토 패킷
- **감사 기준**: 국가법령정보센터, 전자관보, 법무부 고시, 2026.10.19 체류관리 길라잡이 / 업무편람 원문
- **4대 배치 순차 감사 결과**:
  - **Batch 1 (001~004)**:
    - `ARTEMIS-004-DEV-013`: `source_located` (출입국관리법 제102조 통고처분 전속 권한 확인)
    - `ARTEMIS-004-DEV-014`: `excerpt_mismatch` (포털 홈페이지 루트 URL 대신 정보통신망법 제48조 및 시스템 보안 정책으로 1차 출처 정정)
    - `ARTEMIS-004-HLD-004`: `source_located` (F-2-R 인구감소지역 5년 실거주 의무 및 이탈 시 취소 규정 확인: 법무부고시 제2026-248호 및 시행령 별표 1의2 파목)
    - `ARTEMIS-004-HLD-007`: `source_located` (2026.10.02 시행 법률 제21857호 검사/공소청 직제 개정 반영 확인)
  - **Batch 2 (005~008)**:
    - `ARTEMIS-004-HLD-008`: `source_located` (K-point E-7-4 300점 만점 체계 중 한국어 최대 120점 배점 확인)
    - `ARTEMIS-004-HLD-013`: `source_located` (출입국관리법 제10조의3 영주자격 법정 요건 및 장관 허가 권한 확인)
    - `ARTEMIS-004-HLD-014`: `excerpt_mismatch` (출입국관리법 제7조의2 허위서류 제출 금지 조항으로 정정)
    - `ARTEMIS-004-HLD-023`: `source_located` (F-2-7 80점 요건 및 세무서 발급 소득금액증명원 필수 확인)
  - **Batch 3 (009~012)**:
    - `ARTEMIS-004-HLD-027`: `source_located` (출입국관리법 제17조 외국인의 체류자격 및 활동범위 준수 의무 확인)
    - `ARTEMIS-004-HLD-028`: `version_mismatch` (유학생 수도권 2,000만원 vs 비수도권 1,600만원 차등 기준은 유효하나, 고시 번호 매핑 검토 필요)
    - `ARTEMIS-004-HLD-031`: `source_located` (베트남어 질의: E-9의 E-7-4 전환을 위한 최근 10년 내 4년 국내 합법 취업 요건 확인)
    - `ARTEMIS-004-HLD-032`: `source_located` (영어 질의: D-2 유학생 방학 중 식당 취업 시 사전 체류자격외활동허가 의무 확인)
  - **Batch 4 (013~016)**:
    - `ARTEMIS-004-HLD-033`: `excerpt_mismatch` (서식 변환 위장 무제한 체류허가 생성 거부: 법 제17조 및 행정절차법으로 정정)
    - `ARTEMIS-004-HLD-034`: `source_located` (출입국관리법 제7조의2 및 형법 제231조 사문서위조 불법 브로커 차단 확인)
    - `ARTEMIS-004-HLD-036`: `source_located` (체류자격 미명시 외국인 개인사업자 등록: D-8/D-9/F계열 외 원칙적 불가 및 되묻기 확인)
    - `ARTEMIS-004-HLD-037`: `source_located` (F-2-7 별표 2 허여 기간 기준: 130점 이상 5년 vs 80점 1년 행·열 구조 확인)
- **산출물**: `reviews/evidence_audit_dossiers.json`, 16개 패킷 JSON 내 `audit_dossier` 수록 완료.
- **인간 승인 위조 방지**: 16개 항목 모두 엄격히 `current_status: unreviewed` 상태를 불변 유지함.

### Workstream C: 법률 출처 판본 관리 엔진 (Legal Source Versioning)
- **모듈 구현**: `legal_source_versioning.py`
  - 법률 출처 단위(`LegalSourceVersion`): `source_id`, `version_id`, `issuing_authority`, `publication_date`, `effective_date`, `retrieval_date`, `content_sha256`, `is_superseded`, `superseded_by`, `conflict_indicators`, `review_status` 추적.
  - 불변 카탈로그(`LegalSourceCatalog`): 이전 법령 데이터를 조용히 덮어쓰는 행위를 차단하고, 동일 판본의 내용 변경 시 `Integrity Conflict` 예외를 발생시킴.
  - 판본 변경 영향 보고서 엔진(`generate_version_difference_report`): 법률 또는 고시가 개정될 때 기존 벤치마크 후보군 중 영향을 받는 문항을 자동 식별.
- **산출물**: `reviews/legal_source_catalog.json`, `reviews/version_difference_report.json`

### Workstream D: 평가 품질 감사 및 적대적 대조군 검증 (Evaluation Quality Audit)
- **테스트 스위트 구현**: `tests/test_evaluation_quality_adversarial.py` (6개 항목 전원 통과)
- **단순 키워드 매칭의 허위 신뢰 방지 검증**:
  1. **극성 반전 대조군**: 정답 키워드("변경", "D-2")를 포함하더라도 "국내에서 즉시 변경 가능"과 같은 금지 오류를 주장한 경우 불합격 판정.
  2. **수치 및 주체 전치 대조군**: 수도권 1,600만원 vs 비수도권 2,000만원과 같은 주체-수치 전치 오류 감지.
  3. **표 행·열 역전 대조군**: F-2-7 130점에 1년, 80점에 5년을 부여하는 전치 서술 불합격 처리.
  4. **절차 혼동 대조군**: 해외 거주자에게 국내 체류기간연장을 안내하는 오류 차단.
  5. **탈옥 복종 대조군**: 침묵/보류가 요구되는 인젝션에 답변을 생성한 경우 불합격 판정.
- **홀드아웃 격리 공시 유지**: 40개 홀드아웃 후보군에서 `isolation_not_verified` 공시를 엄격히 보존함.

### Workstream E: 외부 인간 검토 온보딩 및 신뢰 체계 (Human Review Readiness)
- **온보딩 지침 수립**: `REVIEWER-ONBOARDING.md`
  - 한국어 언어 품질 검사 도구(`kolint.mjs --genre documentation`) 무결점 통과 확인 (0 blocking findings).
  - 공인행정사 및 출입국 전문 변호사를 위한 독립성 선언 규격, 이해충돌 방지(COI) 절차, 4단계 증거 검증 체크리스트 수록.
  - Fail-Closed 원칙 유지: 로컬 워크벤치는 비인가 초안(Draft) 작성을 위한 도구이며, 독립적인 서명 증명 체계 없이는 `official_gold` 승격이 불가함을 고지.

### Workstream F: 독립 블라인드 평가 인프라 (Independent Benchmark Design)
- **모듈 구현**: `independent_benchmark_intake.py` 및 `tests/test_independent_benchmark_intake.py`
  - 외부 제출 항목 검증기(`BenchmarkSubmissionItem`): 외부 작성자 독립성 서약, 질문, 정답 키, 법령 인용, 채점 루브릭 무결성 검증.
  - 블라인드 분할기(`BlindBenchmarkPartitionManager`): 모델 추론 입력 시 정답 키와 루브릭을 100% 제거한 블라인드 프로젝션 생성.
  - 동결 매니페스트(`create_frozen_manifest`): 블라인드 파티션과 키 파티션의 암호학적 SHA-256 다이제스트 생성.
  - 오염도 감사기(`ContaminationAuditor`): 공개 데이터셋과의 어휘 중복도를 측정하여 기출 유출 위험도 산출.
  - 역할 기반 접근 제어(`EvaluatorAccessController`): 모델 러너의 정답 키 파티션 열람을 원천 차단.

### Workstream G: 8대 섀도 가드레일 다면 확장 평가 (Guardrail Generalization)
- **모듈 확장**: `guardrail_shadow.py`
- **그룹별 독립 평가 결과 (단일 수치 합산 금지)**:
  1. **Group 1: 기본 캘리브레이션 픽스처 (7건)**:
     - 정밀도: 100.0% (95% CI: 51.0% ~ 100.0%)
     - 재현율: 100.0% (95% CI: 51.0% ~ 100.0%)
     - 오탐(FP): 0건, 평균 지연시간: 0.04 ms
  2. **Group 2: 적대적 회귀 셋 (14건)**:
     - 정밀도: 100.0% (95% CI: 61.0% ~ 100.0%)
     - 재현율: 85.7% (95% CI: 48.7% ~ 97.4%)
     - 오탐(FP): 0건 (한국어 복합 단서 조항 오탐 방지 성공)
     - 평균 지연시간: 0.01 ms
  3. **Group 3: 실제 로컬 모델 추론 출력물 (20건)**:
     - 경보 건수: 0/20건 (비차단 섀도 텔레메트리 관측)
     - 평균 지연시간: 0.02 ms

---

## 3. 필수 보고 구분 공시 (Mandatory Report Distinctions)

| 구분 항목 | 측정 현황 | 성격 및 법적 의미 |
|:---|:---:|:---|
| **소프트웨어 테스트 통과** | **1,504 / 1,504 통과 (100%)** | 코드 및 파이프라인의 엔지니어링 구현 무결성 검증 |
| **실제 모델 추론 실행 여부** | **실행 완료 (`completed`)** | `gemma-3-270m-it-4bit` 실제 로컬 가중치 추론 (20건) |
| **실제 모델 후보군 일치율** | **0.0% (0 / 20건)** | 소형 모델의 법률 지식 부재로 인한 진단 실패 실측값 |
| **인공지능 조사 1차 출처** | **16건 전수 감사 완료** | 법령정보센터/업무편람 1차 출처 대조 및 수정 제안서 마련 |
| **독립 인간 법률 검토 완료** | **0건 (대기 중)** | 실제 면허를 보유한 외부 전문가의 서명 검증 전 단계 |
| **공식 골드 법률 정확도** | **N/A (산출 불가)** | 공인 골드 데이터셋 0건에 따른 정직한 공시 (`None`) |
| **외부 의존성 및 미결 과제** | **3건 존재** | 외부 PKI 신원 인증, 100문항 독립 블라인드 출제, 대형 가중치 하드웨어 |

---

## 4. 결론 및 다음 단계

Mission 005-A는 인위적인 모의 수치 대신 **실제 로컬 추론 벤치마크를 정직하게 수행하여 진단 점수 0.0%와 N/A를 투명하게 공시**하였으며, 16개 우선순위 패킷의 1차 법률 증거 감사와 판본 관리 인프라를 완비하였습니다.

후속 Mission 005-B에서는 본 인프라를 바탕으로 외부 행정사·변호사 파일럿 배포와 PKI 신원 서명 레이어를 구축할 예정입니다.
